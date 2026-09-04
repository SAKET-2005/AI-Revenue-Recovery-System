"""Database setup — async SQLAlchemy with SQLite (PostgreSQL-ready)."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        from app.models import transaction, customer, recovery, audit, webhook  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables (for demo reset)."""
    async with engine.begin() as conn:
        from app.models import transaction, customer, recovery, audit, webhook  # noqa
        await conn.run_sync(Base.metadata.drop_all)
