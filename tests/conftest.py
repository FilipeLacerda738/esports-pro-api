"""Testes sempre usam o PostgreSQL descartavel local, nunca o .env de producao."""
import os

# Sobrescreva antes de importar a aplicacao ou o Alembic.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:local-security-test-only@127.0.0.1:55439/esports_security_test?sslmode=disable"
os.environ["API_ACCESS_KEY"] = "local-app-key"
os.environ["ADMIN_API_KEY"] = "local-admin-key"
os.environ["PANDASCORE_API_KEY"] = "local-mocked-key"
os.environ["PANDASCORE_KEYS"] = ""
os.environ["ENVIRONMENT"] = "production"

import pytest
import asyncio
import asyncpg
from alembic.config import Config
from alembic import command


@pytest.fixture(scope="session", autouse=True)
def migrate_local_database():
    command.upgrade(Config("alembic.ini"), "head")
    async def clear_disposable_database():
        conn = await asyncpg.connect(
            host="127.0.0.1", port=55439, user="postgres",
            password="local-security-test-only", database="esports_security_test", ssl=False,
        )
        try:
            await conn.execute("TRUNCATE game_maps, players, matches, teams, leagues, users RESTART IDENTITY CASCADE")
        finally:
            await conn.close()
    asyncio.run(clear_disposable_database())
