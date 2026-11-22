from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import get_settings
from src.storage.models import Base

settings = get_settings()
if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with session_factory() as session:
        yield session
