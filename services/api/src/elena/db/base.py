"""Declarative registry for metadata imports from Alembic."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base."""
