from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

# ✅ VERIFIED: asyncpg connection pooling pattern
DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Async engine with optimized pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,  # minimum concurrent
    max_overflow=20,  # extra when needed
    pool_pre_ping=True,  # validate connections
    pool_recycle=3600,  # recycle hourly
    future=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """Dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
