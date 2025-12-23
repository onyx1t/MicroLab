from sqlalchemy.orm import Session
from sqlalchemy import delete
import httpx

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

# URL Orders Service через API Gateway
ORDERS_SERVICE_URL = "http://nginx_gateway/api/v1/orders"
DELIVERIES_SERVICE_URL = "http://nginx_gateway/api/v1/delivery/"

import bcrypt


def hash_password(password: str) -> str:
    """
    Хеширует переданный пароль используя bcrypt.
    """
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли открытый пароль хешу.
    """
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user.model_dump(exclude_unset=True)

    if 'password' in update_data and update_data['password']:
        update_data['hashed_password'] = hash_password(update_data['password'])
        del update_data['password']

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Обычное удаление только пользователя (оставим как вспомогательное) ---

def _delete_user_only(db: Session, user_id: int) -> bool:
    stmt = delete(User).where(User.id == user_id).returning(User.id)
    deleted_id = db.scalar(stmt)
    if deleted_id is None:
        return False
    db.commit()
    return True


# --- НОВОЕ: каскадное удаление пользователя ---

async def cascade_delete_user(db: Session, user_id: int) -> bool:
    """
    Каскадное удаление пользователя:
    0. Проверяет, нет ли активных доставок по его заказам.
    1. вызывает Orders Service для удаления всех его заказов (которые удалят payments+delivery)
    2. удаляет самого пользователя
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return False

    TIMEOUT = 5.0

    # 0. Проверяем активные доставки через Delivery Service
    async with httpx.AsyncClient() as client:
        try:
            # Получаем ВСЕ заказы пользователя
            orders_url = f"{ORDERS_SERVICE_URL}/"
            resp_orders = await client.get(orders_url, timeout=TIMEOUT)
            if resp_orders.status_code != 200:
                print(f"⚠️ Не удалось получить заказы при удалении пользователя {user_id}: {resp_orders.status_code}")
            else:
                orders = resp_orders.json()
                # Берём только заказы этого пользователя
                user_orders_ids = [o["id"] for o in orders if o["user_id"] == user_id]

                if user_orders_ids:
                    # Получаем все доставки
                    resp_deliveries = await client.get(DELIVERIES_SERVICE_URL, timeout=TIMEOUT)
                    if resp_deliveries.status_code == 200:
                        deliveries = resp_deliveries.json()
                        active_statuses = ["processing", "shipped", "in_transit"]

                        active = [
                            d for d in deliveries
                            if d["order_id"] in user_orders_ids and d["status"] in active_statuses
                        ]

                        if active:
                            from fastapi import HTTPException
                            raise HTTPException(
                                status_code=400,
                                detail="Нельзя удалить пользователя: есть активные доставки по его заказам."
                            )
                    else:
                        print(f"⚠️ Не удалось получить доставки при удалении пользователя {user_id}: {resp_deliveries.status_code}")

        except httpx.RequestError as e:
            from fastapi import HTTPException
            # Если Delivery Service недоступен — лучше не удалять пользователя,
            # чтобы не потерять связь с активными доставками.
            raise HTTPException(
                status_code=503,
                detail=f"Delivery Service недоступен при проверке активных доставок: {e}"
            )

    # 1. Вызываем Orders Service (как раньше)
    async with httpx.AsyncClient() as client:
        try:
            url = f"{ORDERS_SERVICE_URL}/by-user/{user_id}"
            resp = await client.delete(url, timeout=TIMEOUT)
            if resp.status_code not in (200, 204):
                print(f"⚠️ Не удалось удалить заказы пользователя {user_id}: {resp.status_code} {resp.text}")
        except httpx.RequestError as e:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"Orders Service недоступен при удалении пользователя {user_id}: {e}"
            )

    # 2. Удаляем пользователя локально
    stmt = delete(User).where(User.id == user_id).returning(User.id)
    deleted_id = db.scalar(stmt)
    if deleted_id is None:
        db.rollback()
        return False

    db.commit()
    print(f"✅ Каскадно удалён пользователь {user_id} и его заказы/платежи/доставки")
    return True
