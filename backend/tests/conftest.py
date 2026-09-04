"""Pytest configuration and shared fixtures for ReviveAI tests."""

import pytest
import pytest_asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base
from app.ml.predictor import predictor


@pytest.fixture(scope="session", autouse=True)
def load_ml_model():
    """Ensure ML predictor attempts loading artifacts before tests run."""
    predictor.load()


@pytest_asyncio.fixture
async def test_db():
    """Create fresh database tables for test isolation."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
