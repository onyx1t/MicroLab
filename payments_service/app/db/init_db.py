from sqlalchemy.orm import Session
from app.db.database import Base, engine
from app.models.payment import Payment # Импортируем модель платежа

def init_db():
    Base.metadata.create_all(bind=engine)

    db: Session = Session(bind=engine)
    try:
        if db.query(Payment).count() == 0:
            test_payments = [
                # Связываем с order_id (который существует в Orders Service)
                {"order_id": 1, "amount": 100.50, "status": "completed", "method": "card"},
                {"order_id": 2, "amount": 25.00, "status": "completed", "method": "paypal"},
                {"order_id": 3, "amount": 500.99, "status": "failed", "method": "card"},
                {"order_id": 4, "amount": 10.00, "status": "pending", "method": "card"},
                {"order_id": 5, "amount": 75.20, "status": "completed", "method": "cash"},
            ]
            
            for data in test_payments:
                db_payment = Payment(**data)
                db.add(db_payment)
            
            db.commit()
            print("База данных платежей проинициализирована 5 тестовыми записями.")
        else:
            print("База данных платежей уже содержит данные, пропуск инициализации.")
    except Exception as e:
        print(f"Ошибка инициализации БД платежей: {e}")
    finally:
        db.close()