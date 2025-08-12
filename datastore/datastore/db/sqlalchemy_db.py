"""
SQLAlchemy database connection and session management for Nachet
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from .models.base import Base

load_dotenv()


class DatabaseManager:
    """Manages SQLAlchemy database connections and sessions"""
    
    def __init__(self):
        self._sync_engine: Engine | None = None
        self._async_engine: AsyncEngine | None = None
        self._sync_session_factory: sessionmaker[Session] | None = None
        self._async_session_factory: async_sessionmaker[AsyncSession] | None = None
    
    def get_connection_string(self, async_db: bool = False) -> str:
        """Get database connection string"""
        conn_str = os.getenv("NACHET_DATA")
        if not conn_str:
            raise ValueError("NACHET_DATA environment variable is not set")
        
        if async_db:
            # Convert postgresql:// to postgresql+asyncpg://
            if conn_str.startswith("postgresql://"):
                conn_str = conn_str.replace("postgresql://", "postgresql+asyncpg://")
            elif not conn_str.startswith("postgresql+asyncpg://"):
                conn_str = f"postgresql+asyncpg://{conn_str}"
        
        return conn_str
    
    def get_sync_engine(self) -> Engine:
        """Get synchronous SQLAlchemy engine"""
        if self._sync_engine is None:
            conn_str = self.get_connection_string(async_db=False)
            self._sync_engine = create_engine(
                conn_str,
                echo=False,  # Set to True for SQL logging during development
                pool_pre_ping=True,
                pool_recycle=3600,
            )
        return self._sync_engine
    
    def get_async_engine(self) -> AsyncEngine:
        """Get asynchronous SQLAlchemy engine"""
        if self._async_engine is None:
            conn_str = self.get_connection_string(async_db=True)
            self._async_engine = create_async_engine(
                conn_str,
                echo=False,  # Set to True for SQL logging during development
                pool_pre_ping=True,
                pool_recycle=3600,
            )
        return self._async_engine
    
    def get_sync_session_factory(self) -> sessionmaker[Session]:
        """Get synchronous session factory"""
        if self._sync_session_factory is None:
            engine = self.get_sync_engine()
            self._sync_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
            )
        return self._sync_session_factory
    
    def get_async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get asynchronous session factory"""
        if self._async_session_factory is None:
            engine = self.get_async_engine()
            self._async_session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._async_session_factory
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session context manager"""
        session_factory = self.get_async_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self) -> Session:
        """Get synchronous session"""
        session_factory = self.get_sync_session_factory()
        return session_factory()
    
    async def create_tables(self):
        """Create all tables using the async engine"""
        async_engine = self.get_async_engine()
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """Drop all tables using the async engine"""
        async_engine = self.get_async_engine()
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for backward compatibility
def get_sync_engine() -> Engine:
    """Get synchronous SQLAlchemy engine"""
    return db_manager.get_sync_engine()


def get_async_engine() -> AsyncEngine:
    """Get asynchronous SQLAlchemy engine"""
    return db_manager.get_async_engine()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session context manager"""
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_session() -> Session:
    """Get synchronous session"""
    return db_manager.get_sync_session()


async def create_tables():
    """Create all tables"""
    await db_manager.create_tables()


async def drop_tables():
    """Drop all tables"""
    await db_manager.drop_tables()