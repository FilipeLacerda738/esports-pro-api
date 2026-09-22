import os

import pytest

# Never load developer credentials or run background jobs in this suite.
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "DATABASE_SSL": "false",
    "PANDASCORE_API_KEY": "test-only-pandascore-key",
    "API_ACCESS_KEY": "test-only-mobile-key-0000000000000000",
    "SECRET_KEY": "test-only-signing-key-1111111111111111",
    "RATE_LIMIT_STORAGE_URI": "memory://",
    "BACKEND_CORS_ORIGINS": '["https://app.example.com"]',
})

from fastapi.testclient import TestClient
from app.main import app
from app.core.rate_limit import storage


@pytest.fixture(autouse=True)
def reset_state():
    storage.reset()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    # Not entering the context intentionally skips networked lifespan jobs.
    client = TestClient(app)
    yield client
    client.close()
