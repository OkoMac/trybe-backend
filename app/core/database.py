"""Database configuration and connection management"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Base class for models
Base = declarative_base()

# Global engine and session maker
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create database engine"""
    global _engine

    if _engine is None:
        logger.info(f"Creating database engine: {settings.DATABASE_URL.split('@')[-1]}")

        # Choose pool class based on environment
        poolclass = NullPool if settings.is_development else QueuePool

        # Build engine kwargs based on pool class
        engine_kwargs = {
            "echo": settings.DB_ECHO,
            "future": True,
            "poolclass": poolclass,
        }

        # Only add pool config for QueuePool
        if poolclass == QueuePool:
            engine_kwargs.update({
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_pre_ping": True,  # Verify connections before using
                "pool_recycle": 3600,   # Recycle connections after 1 hour
            })

        _engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

        logger.info("Database engine created successfully")

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create async session maker"""
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        logger.info("Session maker created successfully")

    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables"""
    engine = get_engine()

    logger.info("Creating database tables...")

    async with engine.begin() as conn:
        # Import all models to register them with Base
        from app.models import user  # noqa: F401
        from app.models import opportunity  # noqa: F401
        from app.models import match  # noqa: F401
        from app.models import payment  # noqa: F401
        from app.models import message  # noqa: F401
        from app.models import notification  # noqa: F401
        from app.models import learning  # noqa: F401
        from app.models import analytics  # noqa: F401
        from app.models import report  # noqa: F401
        # Add other model imports here

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def close_db() -> None:
    """Close database connections"""
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Closing database connections...")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("Database connections closed")


# Health check function
async def check_db_health() -> bool:
    """Check if database connection is healthy"""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
