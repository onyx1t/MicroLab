from sqlalchemy.orm import Session
from app.db.database import Base, engine
from app.models.delivery import Delivery

def init_db():
    Base.metadata.create_all(bind=engine)

    db: Session = Session(bind=engine)
    try:
        if db.query(Delivery).count() == 0:
            test_deliveries = [
                # Связываем с order_id из Orders Service
                {"order_id": 1, "status": "shipped", "address": "ул. Пушкина, 10"},
                {"order_id": 2, "status": "delivered", "address": "пр. Ленина, 25"},
                {"order_id": 3, "status": "processing", "address": "ул. Мира, 5"},
            ]
            
            for data in test_deliveries:
                db_delivery = Delivery(**data)
                db.add(db_delivery)
            
            db.commit()
            print("База данных доставок проинициализирована 3 тестовыми записями.")
        else:
            print("База данных доставок уже содержит данные, пропуск инициализации.")
    except Exception as e:
        print(f"Ошибка инициализации БД доставок: {e}")
    finally:
        db.close()