from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config

# Создаем движок SQLAlchemy
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
