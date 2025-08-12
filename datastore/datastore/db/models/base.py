"""
Base SQLAlchemy configuration for Nachet models
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    
    metadata = MetaData(schema="nachet_0.0.13")