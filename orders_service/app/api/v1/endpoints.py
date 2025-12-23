from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.order import OrderInDB, OrderCreate, OrderUpdate
from app.crud import orders as crud_orders

router = APIRouter()


# CREATE
@router.post("/", response_model=OrderInDB, status_code=status.HTTP_201_CREATED)
async def create_order_route(order: OrderCreate, db: Session = Depends(get_db)):
    """Создание нового заказа с валидацией user_id в Users Service."""
    try:
        return await crud_orders.create_order(db=db, order=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Непредвиденная ошибка при создании заказа: {e}"
        )


# READ ALL
@router.get("/", response_model=List[OrderInDB])
def read_orders_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка всех заказов."""
    orders = crud_orders.get_orders(db, skip=skip, limit=limit)
    return orders


# READ ONE
@router.get("/{order_id}", response_model=OrderInDB)
def read_order_route(order_id: int, db: Session = Depends(get_db)):
    """Получение заказа по ID."""
    db_order = crud_orders.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


# UPDATE
@router.put("/{order_id}", response_model=OrderInDB)
def update_order_route(order_id: int, order: OrderUpdate, db: Session = Depends(get_db)):
    """Обновление существующего заказа по ID."""
    updated_order = crud_orders.update_order(db, order_id=order_id, order=order)
    if updated_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return updated_order


# DELETE (КАСКАДНОЕ)
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_route(order_id: int, db: Session = Depends(get_db)):
    """
    Каскадное удаление заказа:
    - удаляет платеж и доставку через Payments и Delivery services
    - затем удаляет заказ локально
    """
    success = await crud_orders.cascade_delete_order(db, order_id=order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return


# --- PATCH /status остаётся как раньше (если он у тебя уже есть) ---

@router.patch("/{order_id}/status", response_model=OrderInDB)
async def update_order_status_route(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    """
    Обновление статуса заказа.
    (Автоматическое создание доставки мы решили НЕ включать.)
    """
    allowed_statuses = ["pending", "paid", "shipped", "completed", "cancelled"]
    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Разрешены: {allowed_statuses}"
        )

    updated_order = crud_orders.update_order_status(db, order_id=order_id, new_status=status)
    if updated_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return updated_order

@router.delete("/by-user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_orders_by_user_route(user_id: int, db: Session = Depends(get_db)):
    """
    Каскадно удаляет все заказы пользователя:
    - вызывается Users Service при удалении пользователя
    """
    await crud_orders.cascade_delete_orders_by_user(db, user_id=user_id)
    # Даже если заказов не было, возвращаем 204 — это нормально
    return