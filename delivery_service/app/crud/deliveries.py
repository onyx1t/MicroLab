import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.models.delivery import Delivery
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate

ORDERS_SERVICE_URL = "http://nginx_gateway/api/v1/orders"


# --- Межсервисное общение ---

async def verify_order_ready_for_delivery(order_id: int):
    """
    Проверяет статус заказа перед созданием доставки.
    Принимает статусы: 'paid', 'completed', 'shipped'.
    """
    url = f"{ORDERS_SERVICE_URL}/{order_id}"
    TIMEOUT = 5.0

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=TIMEOUT)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Заказ не найден."
                )

            order_data = response.json()

            allowed_statuses = ['paid', 'completed', 'shipped']
            if order_data['status'] not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Заказ имеет статус '{order_data['status']}' и не готов к доставке. "
                        f"Требуется один из: {allowed_statuses}"
                    )
                )

            return True

        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Service Unavailable"
            )


# --- CRUD ---

# CREATE
async def create_delivery(db: Session, delivery: DeliveryCreate):
    # Проверяем готовность заказа к доставке
    await verify_order_ready_for_delivery(delivery.order_id)

    db_delivery = Delivery(
        order_id=delivery.order_id,
        status="processing",
        address=delivery.address
    )

    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    return db_delivery


# READ ALL
def get_deliveries(db: Session, skip: int = 0, limit: int = 100):
    return db.scalars(select(Delivery).offset(skip).limit(limit)).all()


# READ ONE
def get_delivery(db: Session, delivery_id: int):
    return db.get(Delivery, delivery_id)


# UPDATE
def update_delivery(db: Session, delivery_id: int, delivery: DeliveryUpdate):
    db_delivery = db.get(Delivery, delivery_id)
    if not db_delivery:
        return None

    update_data = delivery.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_delivery, key, value)

    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    return db_delivery


# DELETE по ID
def delete_delivery(db: Session, delivery_id: int):
    stmt = delete(Delivery).where(Delivery.id == delivery_id).returning(Delivery.id)
    if db.scalar(stmt):
        db.commit()
        return True
    return False


# --- НОВОЕ: удаление по order_id для каскадного сценария ---

def delete_delivery_by_order_id(db: Session, order_id: int) -> bool:
    """
    Удаляет запись о доставке по order_id.
    Используется для каскадного удаления (когда удаляется заказ или пользователь).
    """
    stmt = delete(Delivery).where(Delivery.order_id == order_id).returning(Delivery.id)
    deleted_id = db.scalar(stmt)
    if deleted_id:
        db.commit()
        print(f"✅ Доставка для order_id={order_id} удалена")
        return True

    # Записи может не быть — это не ошибка для каскадного сценария
    print(f"ℹ️ Доставка для order_id={order_id} не найдена, ничего не удаляем")
    return False
