from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.payment import PaymentCreate, PaymentInDB, PaymentUpdate
from app.crud import payments as crud_payments

router = APIRouter()


# CREATE
@router.post("/", response_model=PaymentInDB, status_code=status.HTTP_201_CREATED)
async def create_payment_route(payment: PaymentCreate, db: Session = Depends(get_db)):
    return await crud_payments.create_payment(db=db, payment=payment)


# READ ALL
@router.get("/", response_model=List[PaymentInDB])
def read_payments_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_payments.get_payments(db, skip=skip, limit=limit)


# READ ONE
@router.get("/{payment_id}", response_model=PaymentInDB)
def read_payment_route(payment_id: int, db: Session = Depends(get_db)):
    db_payment = crud_payments.get_payment(db, payment_id=payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment


# UPDATE
@router.put("/{payment_id}", response_model=PaymentInDB)
def update_payment_route(payment_id: int, payment: PaymentUpdate, db: Session = Depends(get_db)):
    db_payment = crud_payments.update_payment(db, payment_id=payment_id, payment=payment)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment


# DELETE по ID
@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_route(payment_id: int, db: Session = Depends(get_db)):
    success = crud_payments.delete_payment(db, payment_id=payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")
    return


# --- НОВОЕ: удаление по order_id для каскадного сценария ---

@router.delete("/by-order/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_by_order_route(order_id: int, db: Session = Depends(get_db)):
    """
    Удаляет платеж по order_id.
    Используется другими микросервисами (Orders, Users) при каскадном удалении.
    """
    crud_payments.delete_payment_by_order_id(db, order_id=order_id)
    # Даже если платежа не было, возвращаем 204 — это нормально для каскадного удаления
    return
