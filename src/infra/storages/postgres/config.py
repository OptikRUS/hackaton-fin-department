from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings

async_engine = create_async_engine(
    settings.POSTGRES.DSN.get_secret_value(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
async_session = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
