from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    
    # ID заказа, который доставляется
    order_id = Column(Integer, unique=True, nullable=False, index=True) 
    
    status = Column(String, default="processing") # processing, shipped, in_transit, delivered, failed
    address = Column(String, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())