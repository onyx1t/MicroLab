import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ИСПОЛЬЗУЕМ ПЕРЕМЕННЫЕ ДЛЯ DELIVERY DB
POSTGRES_USER = os.getenv("DELIVERY_POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("DELIVERY_POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("DELIVERY_POSTGRES_DB")
DATABASE_HOST = os.getenv("DELIVERY_DATABASE_HOST")
DATABASE_PORT = os.getenv("DELIVERY_DATABASE_PORT")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{POSTGRES_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()