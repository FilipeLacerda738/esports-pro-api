import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://esports_backend:local-backend-test-only@127.0.0.1:55439/esports_security_test?sslmode=disable"
os.environ["MIGRATION_DATABASE_URL"] = "postgresql+asyncpg://postgres:local-security-test-only@127.0.0.1:55439/esports_security_test?sslmode=disable"
os.environ["API_ACCESS_KEY"] = "local-app-key"
os.environ["ADMIN_API_KEY"] = "local-admin-key"
os.environ["PANDASCORE_API_KEY"] = "local-mocked-key"
os.environ["PANDASCORE_KEYS"] = ""
os.environ["ENVIRONMENT"] = "production"

import pytest
import asyncio
import asyncpg
from pathlib import Path
from alembic.config import Config
from alembic import command


@pytest.fixture(scope="session", autouse=True)
def migrate_local_database():
    async def prepare_roles():
        conn = await asyncpg.connect(host="127.0.0.1", port=55439, user="postgres", password="local-security-test-only", database="esports_security_test", ssl=False)
        try:
            for role in ("anon", "authenticated", "service_role", "supabase_admin"):
                if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                    await conn.execute(f"CREATE ROLE {role} NOLOGIN")
        finally:
            await conn.close()
    asyncio.run(prepare_roles())
    command.upgrade(Config("alembic.ini"), "head")
    async def clear_disposable_database():
        conn = await asyncpg.connect(
            host="127.0.0.1", port=55439, user="postgres",
            password="local-security-test-only", database="esports_security_test", ssl=False,
        )
        try:
            await conn.execute("TRUNCATE game_maps, players, matches, teams, leagues, users RESTART IDENTITY CASCADE")
            async with conn.transaction():
                await conn.execute(Path("security/harden_database.sql").read_text(encoding="utf-8"))
                await conn.execute("ALTER ROLE esports_backend LOGIN PASSWORD 'local-backend-test-only'")
        finally:
            await conn.close()
    asyncio.run(clear_disposable_database())
