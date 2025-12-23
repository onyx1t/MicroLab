from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.user import UserInDB, UserCreate, UserUpdate
from app.crud import users as crud_users

router = APIRouter()


@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Создание нового пользователя."""
    try:
        db_user = crud_users.get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        created_user = crud_users.create_user(db=db, user=user)
        return created_user

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Error creating user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during user creation"
        )


@router.get("/", response_model=List[UserInDB])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка пользователей."""
    users = crud_users.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserInDB)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Получение пользователя по ID."""
    db_user = crud_users.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@router.put("/{user_id}", response_model=UserInDB)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """Обновление данных пользователя."""
    db_user = crud_users.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


# --- НОВОЕ: каскадное удаление пользователя ---

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Каскадное удаление пользователя:
    - удаляет все его заказы (Orders → Payments + Delivery)
    - затем удаляет пользователя
    """
    success = await crud_users.cascade_delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return
