from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

# SQLAlchemy engine that manages database connections
engine = create_async_engine(
    settings.database_uri, 
    pool_pre_ping=True,
    echo=settings.environment == "development"
)

# Session factory to create session/db
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False, # SQLAlchemy does not expire the ORM object's attributes after a commit
)


# DeclarativeBase provides SQLAlchemy's declarative mapping system
class Base(DeclarativeBase):
    pass


# Dependency that provide db/session for each request
# and ensure that db/session is closed afterward
async def get_db() -> AsyncGenerator[AsyncSession | None]:
    async with AsyncSessionLocal() as session:
        yield session
