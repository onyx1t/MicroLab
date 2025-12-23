from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeliveryCreate(BaseModel):
    order_id: int
    address: str

class DeliveryUpdate(BaseModel):
    status: Optional[str] = None
    address: Optional[str] = None

class DeliveryInDB(BaseModel):
    id: int
    order_id: int
    status: str
    address: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True