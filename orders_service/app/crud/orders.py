import httpx

from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate

# URL для доступа к сервису пользователей через Docker сеть
USERS_SERVICE_URL = "http://users_service_container:8000"

# URL для сервисов платежей и доставки через API Gateway
PAYMENTS_SERVICE_URL = "http://nginx_gateway/api/v1/payments"
DELIVERY_SERVICE_URL = "http://nginx_gateway/api/v1/delivery"


# --- Межсервисное общение с Users Service ---

async def check_user_exists(user_id: int) -> bool:
    """Отправляет HTTP-запрос к Users Service для проверки существования пользователя."""
    url = f"{USERS_SERVICE_URL}/api/v1/users/{user_id}"
    TIMEOUT = 5.0

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=TIMEOUT)

            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при проверке Users Service: получено {response.status_code}"
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Users Service временно недоступен или таймаут ({TIMEOUT}s): {e}"
            )


# --- CRUD-операции ---

# CREATE
async def create_order(db: Session, order: OrderCreate):
    # ПРОВЕРКА СУЩЕСТВОВАНИЯ ПОЛЬЗОВАТЕЛЯ
    user_exists = await check_user_exists(order.user_id)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {order.user_id} не найден. Невозможно создать заказ."
        )

    db_order = Order(**order.model_dump(), status="pending")
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


# READ ONE
def get_order(db: Session, order_id: int):
    return db.get(Order, order_id)


# READ ALL
def get_orders(db: Session, skip: int = 0, limit: int = 100):
    """Получение списка всех заказов с пагинацией."""
    return db.scalars(select(Order).offset(skip).limit(limit)).all()


# UPDATE (полное обновление по схеме)
def update_order(db: Session, order_id: int, order: OrderUpdate):
    """Обновление существующего заказа."""
    db_order = db.get(Order, order_id)
    if db_order is None:
        return None

    update_data = order.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_order, key, value)

    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


# --- НОВОЕ: каскадное удаление заказа ---

async def cascade_delete_order(db: Session, order_id: int) -> bool:
    """
    Каскадное удаление заказа:
    1. Удаляет платеж по order_id в Payments Service
    2. Удаляет доставку по order_id в Delivery Service
    3. Удаляет сам заказ в Orders Service
    """
    # 1. Проверяем, существует ли заказ
    db_order = db.get(Order, order_id)
    if db_order is None:
        return False

    TIMEOUT = 5.0

    # 2. Удаляем платеж
    async with httpx.AsyncClient() as client:
        try:
            payments_url = f"{PAYMENTS_SERVICE_URL}/by-order/{order_id}"
            resp_pay = await client.delete(payments_url, timeout=TIMEOUT)
            # Ожидаем 204 или 200, но даже если платежа нет — это не ошибка
            if resp_pay.status_code not in (200, 204):
                print(f"⚠️ Не удалось удалить платеж для order_id={order_id}: {resp_pay.status_code} {resp_pay.text}")
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payments Service недоступен при удалении заказа {order_id}: {e}"
            )

    # 3. Удаляем доставку
    async with httpx.AsyncClient() as client:
        try:
            delivery_url = f"{DELIVERY_SERVICE_URL}/by-order/{order_id}"
            resp_del = await client.delete(delivery_url, timeout=TIMEOUT)
            if resp_del.status_code not in (200, 204):
                print(f"⚠️ Не удалось удалить доставку для order_id={order_id}: {resp_del.status_code} {resp_del.text}")
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Delivery Service недоступен при удалении заказа {order_id}: {e}"
            )

    # 4. Удаляем заказ локально
    stmt = delete(Order).where(Order.id == order_id).returning(Order.id)
    deleted_id = db.scalar(stmt)
    if deleted_id is None:
        db.rollback()
        return False

    db.commit()
    print(f"✅ Каскадно удалён заказ {order_id} и связанные данные")
    return True


# --- Обновление статуса (для payments / delivery) ---

def update_order_status(db: Session, order_id: int, new_status: str):
    """Обновление только статуса заказа."""
    db_order = db.get(Order, order_id)
    if db_order is None:
        return None

    db_order.status = new_status
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

async def cascade_delete_orders_by_user(db: Session, user_id: int) -> int:
    """
    Каскадно удаляет все заказы пользователя:
    для каждого заказа:
      - удаляет платеж (Payments Service)
      - удаляет доставку (Delivery Service)
      - удаляет заказ локально
    Возвращает количество удалённых заказов.
    """
    # Находим все заказы пользователя
    orders = db.scalars(select(Order).where(Order.user_id == user_id)).all()
    if not orders:
        print(f"ℹ️ У пользователя {user_id} нет заказов для каскадного удаления")
        return 0

    TIMEOUT = 5.0

    async with httpx.AsyncClient() as client:
        for order in orders:
            order_id = order.id

            # 1. Удаляем платеж
            try:
                payments_url = f"{PAYMENTS_SERVICE_URL}/by-order/{order_id}"
                resp_pay = await client.delete(payments_url, timeout=TIMEOUT)
                if resp_pay.status_code not in (200, 204):
                    print(f"⚠️ Не удалось удалить платеж для order_id={order_id}: {resp_pay.status_code} {resp_pay.text}")
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Payments Service недоступен при удалении заказов пользователя {user_id}: {e}"
                )

            # 2. Удаляем доставку
            try:
                delivery_url = f"{DELIVERY_SERVICE_URL}/by-order/{order_id}"
                resp_del = await client.delete(delivery_url, timeout=TIMEOUT)
                if resp_del.status_code not in (200, 204):
                    print(f"⚠️ Не удалось удалить доставку для order_id={order_id}: {resp_del.status_code} {resp_del.text}")
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Delivery Service недоступен при удалении заказов пользователя {user_id}: {e}"
                )

            # 3. Удаляем сам заказ
            stmt = delete(Order).where(Order.id == order_id).returning(Order.id)
            deleted_id = db.scalar(stmt)
            if deleted_id is None:
                print(f"⚠️ Не удалось удалить заказ {order_id} пользователя {user_id}")

    db.commit()
    print(f"✅ Каскадно удалены {len(orders)} заказ(ов) пользователя {user_id}")
    return len(orders)