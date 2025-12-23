import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

# Важно: Внутри Docker сети мы обращаемся к Nginx Gateway,
# чтобы наш запрос к заказам тоже прошел через балансировщик!
ORDERS_SERVICE_URL = "http://nginx_gateway/api/v1/orders"
DELIVERY_SERVICE_URL = "http://nginx_gateway/api/v1/delivery"


# --- Межсервисное общение с Orders Service ---

async def verify_order_can_be_paid(order_id: int):
    """
    Проверяет, существует ли заказ и находится ли он в статусе 'pending'.
    """
    url = f"{ORDERS_SERVICE_URL}/{order_id}"
    TIMEOUT = 5.0

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=TIMEOUT)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Заказ {order_id} не найден."
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось получить данные о заказе."
                )

            order_data = response.json()

            # ВАЛИДАЦИЯ БИЗНЕС-ЛОГИКИ
            if order_data['status'] != 'pending':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Заказ {order_id} имеет статус '{order_data['status']}' и не может быть оплачен."
                )

            return True

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Сервис заказов недоступен: {e}"
            )


async def update_order_status_after_payment(order_id: int):
    """
    Отправляет запрос в Orders Service для обновления статуса на 'paid'.
    """
    url = f"{ORDERS_SERVICE_URL}/{order_id}/status"
    params = {"status": "paid"}
    TIMEOUT = 5.0

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, params=params, timeout=TIMEOUT)

            if response.status_code == 200:
                print(f"✅ Статус заказа {order_id} обновлен на 'paid'")
                return response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Не удалось обновить статус заказа: {response.status_code}"
                )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Orders Service недоступен: {e}"
            )


async def create_delivery_for_order(order_id: int):
    """
    Автоматически создает доставку для оплаченного заказа.
    """
    url = f"{DELIVERY_SERVICE_URL}/"
    TIMEOUT = 5.0

    delivery_payload = {
        "order_id": order_id,
        "address": "Адрес из заказа"  # здесь можно подтягивать реальный адрес из Orders
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=delivery_payload,
                timeout=TIMEOUT
            )

            if response.status_code == 201:
                print(f"✅ Доставка для заказа {order_id} создана автоматически")
                return response.json()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось создать доставку: {response.status_code} - {response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Delivery Service недоступен: {e}"
            )


# --- CRUD Операции ---

# CREATE (улучшенная версия с автоматизацией)
async def create_payment(db: Session, payment: PaymentCreate):
    """
    Создание платежа с автоматическим:
    1. Обновлением статуса заказа на 'paid'
    2. Созданием доставки
    """
    # 1. Проверяем валидность заказа (должен быть в статусе 'pending')
    await verify_order_can_be_paid(payment.order_id)

    # 2. Создаем платеж
    db_payment = Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        method=payment.method,
        status="success"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    # 3. Обновляем статус заказа
    try:
        await update_order_status_after_payment(payment.order_id)
    except Exception as e:
        print(f"⚠️ Предупреждение: Платеж создан, но не удалось обновить статус заказа: {e}")

    # 4. Создаем доставку
    try:
        delivery_data = await create_delivery_for_order(payment.order_id)
        print(f"✅ Доставка автоматически создана: {delivery_data}")
    except Exception as e:
        print(f"⚠️ Предупреждение: Платеж создан, но не удалось создать доставку: {e}")

    return db_payment


# READ ALL
def get_payments(db: Session, skip: int = 0, limit: int = 100):
    return db.scalars(select(Payment).offset(skip).limit(limit)).all()


# READ ONE
def get_payment(db: Session, payment_id: int):
    return db.get(Payment, payment_id)


# UPDATE
def update_payment(db: Session, payment_id: int, payment: PaymentUpdate):
    db_payment = db.get(Payment, payment_id)
    if not db_payment:
        return None

    update_data = payment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_payment, key, value)

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


# DELETE по ID
def delete_payment(db: Session, payment_id: int):
    stmt = delete(Payment).where(Payment.id == payment_id).returning(Payment.id)
    deleted_id = db.scalar(stmt)
    if deleted_id:
        db.commit()
        return True
    return False


# --- НОВОЕ: удаление по order_id (для каскадного удаления) ---

def delete_payment_by_order_id(db: Session, order_id: int) -> bool:
    """
    Удаляет платеж, связанный с конкретным order_id.
    Используется для каскадного удаления (когда удаляется заказ или пользователь).
    """
    stmt = delete(Payment).where(Payment.order_id == order_id).returning(Payment.id)
    deleted_id = db.scalar(stmt)
    if deleted_id:
        db.commit()
        print(f"✅ Платеж для order_id={order_id} удалён")
        return True

    # Платёж может отсутствовать — это не ошибка для каскадного сценария
    print(f"ℹ️ Платеж для order_id={order_id} не найден, ничего не удаляем")
    return False
