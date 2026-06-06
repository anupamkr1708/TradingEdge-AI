"""
Supabase PostgreSQL Integration

Manages SQLAlchemy engine, connection pool, and session lifecycle.
"""

from typing import Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import Pool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Sync engine (for migrations and health checks)
engine = create_engine(
    settings.SUPABASE_DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
    future=True,
)

# Async engine (for application)
async_engine = create_async_engine(
    settings.SUPABASE_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)

# Session factories
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new database connection is established"""
    logger.debug("Database connection established")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI async dependency for database sessions.
    
    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Model))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database transaction rolled back: {e}")
            raise


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            result = db.execute(text("SELECT 1")).scalar()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions outside FastAPI"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise
    finally:
        db.close()


def check_database_health() -> tuple[bool, str]:
    """Verify database connectivity"""
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1")).scalar()
        return True, "Database connection healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"Database unhealthy: {str(e)}"


def init_db() -> None:
    """Initialize database connection pool"""
    logger.info("Initializing database connection pool")
    
    healthy, message = check_database_health()
    if not healthy:
        raise RuntimeError(f"Database initialization failed: {message}")
    
    logger.info("Database initialized successfully")


def close_db() -> None:
    """Close database connections"""
    logger.info("Closing database connection pool")
    engine.dispose()


async def close_async_db() -> None:
    """Close async database connections"""
    logger.info("Closing async database connection pool")
    await async_engine.dispose()
