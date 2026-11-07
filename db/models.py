from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Recipe(Base):
    __tablename__ = "рецепты"

    id = Column(Integer, primary_key=True, index=True)
    название_блюда = Column(String, index=True)
    описание = Text
    время_готовки_минут = Column(Integer)
    сложность = Column(String)
    порций = Column(Integer)
    кухня = Column(String)
    # Пищевая ценность как JSON
    пищевая_ценность = Column(JSON)
    совет_шефа = Text
    рекомендация_подачи = Text
    image_url = String
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "пользователи"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = String
    first_name = String
    last_name = String
    created_at = Column(DateTime, default=datetime.utcnow)

class Image(Base):
    __tablename__ = "изображения"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Text
    url = String
    created_at = Column(DateTime, default=datetime.utcnow)