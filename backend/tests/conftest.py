"""Pytest configuration and shared fixtures for ReviveAI tests."""

import pytest
import pytest_asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db
from app.ml.predictor import predictor
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///test_reviveai.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def load_ml_model():
    """Ensure ML predictor attempts loading artifacts before tests run."""
    predictor.load()


@pytest_asyncio.fixture
async def test_db():
    """Create fresh database tables in isolated test_reviveai.db for test isolation."""
    async def _override_get_db():
        async with test_async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
