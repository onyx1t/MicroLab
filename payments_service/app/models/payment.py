from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # ID заказа, который оплачивается
    order_id = Column(Integer, unique=True, nullable=False, index=True) 
    
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending") # pending, completed, failed, refunded
    method = Column(String, nullable=False) # card, paypal, cash, etc.
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())