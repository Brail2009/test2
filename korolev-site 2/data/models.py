"""
Модели БД.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Setting(Base):
    """Key/value для всех редактируемых текстов и контактов."""
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, default="")


class Review(Base):
    """Отзывы клиентов. Показываются, если show_reviews=1 и есть опубликованные."""
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    author = Column(String(200), nullable=False)
    text = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContactRequest(Base):
    """Заявки с формы обратной связи."""
    __tablename__ = "contact_requests"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(300), nullable=False)
    service = Column(String(200), default="")
    message = Column(Text, nullable=False)
    consent = Column(Boolean, default=False)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(500), default="")
    status = Column(String(50), default="new", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)