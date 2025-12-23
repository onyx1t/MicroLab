from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, ProgrammingError
from app.db.database import Base, engine
from app.models.order import Order

def init_db():
    try:
        # Создание всех таблиц (с обработкой race condition)
        Base.metadata.create_all(bind=engine)
    except (IntegrityError, ProgrammingError) as e:
        # Игнорируем ошибки, если таблица уже создана другой репликой
        print(f"Таблица уже существует (создана другой репликой): {e}")
    
    # Заполнение тестовыми данными
    db: Session = Session(bind=engine)
    
    try:
        if db.query(Order).count() == 0:
            test_orders = [
                {"user_id": 1, "total_amount": 100.50, "status": "delivered"},
                {"user_id": 1, "total_amount": 25.00, "status": "shipped"},
                {"user_id": 2, "total_amount": 500.99, "status": "processing"},
                {"user_id": 3, "total_amount": 10.00, "status": "pending"},
                {"user_id": 4, "total_amount": 75.20, "status": "delivered"},
            ]
            
            for data in test_orders:
                db_order = Order(**data)
                db.add(db_order)
            
            db.commit()
            print("База данных заказов проинициализирована 5 тестовыми записями.")
        else:
            print("База данных заказов уже содержит данные, пропуск инициализации.")
    
    except Exception as e:
        print(f"Ошибка инициализации БД заказов: {e}")
        db.rollback()
    finally:
        db.close()
