from sqlalchemy.orm import Session
from app.db.database import Base, engine
from app.models.user import User

def init_db():
    # 1. Создание всех таблиц
    Base.metadata.create_all(bind=engine)
    
    # 2. Заполнение тестовыми данными
    db: Session = Session(bind=engine)
    
    try:
        if db.query(User).count() == 0:
            test_users = [
                {
                    "full_name": "Иванов Иван Иванович",
                    "email": "ivanov@example.com",
                    "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
                },
                {
                    "full_name": "Петрова Анна Сергеевна",
                    "email": "anna.petrova@company.org",
                    "hashed_password": "$2a$10$N9qo8uLOickgx2ZMRZoMyeL7Wbh3Yx7b2JQ3Jk5Vz3eFJ6D1S5mOa"
                },
                {
                    "full_name": "Сидоров Алексей",
                    "email": "alex.sidorov@mail.ru",
                    "hashed_password": "$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"
                },
                {
                    "full_name": "Козлова Мария Дмитриевна",
                    "email": "m.kozlova@university.edu",
                    "hashed_password": "$2b$12$SDic3R5q7vzh5bQYVXqBDOeR2xVjLk/WMlDvHwQpN8tFgJZ6rYs1G"
                },
                {
                    "full_name": "Григорьев Дмитрий",
                    "email": "d.grigorev@business.com",
                    "hashed_password": "$2a$10$5sR3ZkLm9Jv6tR8cN1qVUeB2wX3yD4zA5C6E7F8G9H0I1J2K3L4M5N6"
                }
            ]
            
            for data in test_users:
                db_user = User(
                    full_name=data["full_name"],
                    email=data["email"],
                    hashed_password=data["hashed_password"],  # ← ИСПРАВЛЕНО
                    is_active=True
                )
                db.add(db_user)
            
            db.commit()
            print("База данных пользователей проинициализирована 5 тестовыми записями.")
        else:
            print("База данных уже содержит данные, пропуск инициализации.")
    
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")
    finally:
        db.close()
