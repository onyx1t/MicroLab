from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.delivery import DeliveryInDB, DeliveryCreate, DeliveryUpdate
from app.crud import deliveries as crud_deliveries

router = APIRouter()


@router.post("/", response_model=DeliveryInDB, status_code=status.HTTP_201_CREATED)
async def create_delivery_route(delivery: DeliveryCreate, db: Session = Depends(get_db)):
    """Создание новой записи о доставке. Проверяет order_id в Orders Service."""
    return await crud_deliveries.create_delivery(db=db, delivery=delivery)


@router.get("/", response_model=List[DeliveryInDB])
def read_deliveries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка всех записей о доставке."""
    deliveries = crud_deliveries.get_deliveries(db, skip=skip, limit=limit)
    return deliveries


@router.get("/{delivery_id}", response_model=DeliveryInDB)
def read_delivery(delivery_id: int, db: Session = Depends(get_db)):
    """Получение записи о доставке по ID."""
    db_delivery = crud_deliveries.get_delivery(db, delivery_id=delivery_id)
    if db_delivery is None:
        raise HTTPException(status_code=404, detail="Запись о доставке не найдена")
    return db_delivery


@router.put("/{delivery_id}", response_model=DeliveryInDB)
def update_delivery_route(delivery_id: int, delivery: DeliveryUpdate, db: Session = Depends(get_db)):
    """Обновление статуса или адреса доставки."""
    db_delivery = crud_deliveries.update_delivery(db, delivery_id=delivery_id, delivery=delivery)
    if db_delivery is None:
        raise HTTPException(status_code=404, detail="Запись о доставке не найдена")
    return db_delivery


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_route(delivery_id: int, db: Session = Depends(get_db)):
    success = crud_deliveries.delete_delivery(db, delivery_id=delivery_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return


# --- НОВОЕ: удаление по order_id для каскадного сценария ---

@router.delete("/by-order/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_by_order_route(order_id: int, db: Session = Depends(get_db)):
    """
    Удаляет доставку по order_id.
    Используется другими микросервисами (Orders, Users) при каскадном удалении.
    """
    crud_deliveries.delete_delivery_by_order_id(db, order_id=order_id)
    # Даже если доставки не было, возвращаем 204 — это нормально для каскада
    return
