import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
import structlog
from config import settings

logger = structlog.get_logger(__name__)

Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        # Convert sync PostgreSQL URL to async
        database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        
        self.engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            async with self.engine.begin() as conn:
                # Import all models to ensure they're registered
                from database import models
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
        logger.info("Database connection closed")

    async def check_connection(self):
        """Check if database is accessible"""
        try:
            async with self.async_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Database connection check failed", error=str(e))
            raise

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.async_session()

# Dependency for FastAPI
async def get_db_session():
    """Dependency to get database session"""
    from main import app
    db_manager = app.state.db_manager
    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()