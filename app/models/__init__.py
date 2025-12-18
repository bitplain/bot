"""Модели приложения."""
from app.core.db import Base
from app.models.knowledge_base import Employee

__all__ = ["Base", "Employee"]
