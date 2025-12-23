from pydantic import BaseModel
from typing import Optional

# Схема для создания
class UserCreate(BaseModel):
    full_name: str
    email: str  # ← Временно убрали EmailStr
    password: str
    is_active: bool = True

# Схема для обновления
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

# Схема для чтения (БЕЗ пароля для безопасности!)
class UserInDB(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True
