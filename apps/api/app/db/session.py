from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from app.core.config import get_settings
engine=create_async_engine(get_settings().database_url,pool_pre_ping=True,pool_size=10,max_overflow=20)
SessionLocal=async_sessionmaker(engine,expire_on_commit=False)
async def get_db():
    async with SessionLocal() as session:
        yield session
