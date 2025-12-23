from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrderCreate(BaseModel):
    user_id: int
    total_amount: float

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    total_amount: Optional[float] = None

class OrderInDB(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # В старых версиях Pydantic - orm_mode = True