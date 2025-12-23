from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    method: str

class PaymentUpdate(BaseModel):
    status: Optional[str] = None

class PaymentInDB(BaseModel):
    id: int
    order_id: int
    amount: float
    status: str
    method: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True