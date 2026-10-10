import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.db.connection import database_options
from app.db.session import SessionLocal, engine
from app.models.team import Team
from app.models.match import Match
from app.models.league import League
from app.api.v1 import matches, system
from app.services.pandascore import sync as sync_service


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local") as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_android_reads_with_existing_key(client):
    async with SessionLocal() as db:
        team = Team(name="Local security team", game="CSGO")
        league = League(name="Local security league")
        db.add_all([team, league])
        await db.flush()
        match = Match(pandascore_id=987654321, game="CSGO", status="running", team_a_id=team.id, league_id=league.id)
        db.add(match)
        await db.commit()
        match_id = match.id
    headers = {"X-API-Key": "local-app-key"}
    listing = await client.get("/api/v1/matches/", headers=headers)
    assert listing.status_code == 200
    assert {"total", "page", "size", "has_more", "items"} == set(listing.json())
    assert any(item["id"] == match_id for item in listing.json()["items"])
    detail = await client.get(f"/api/v1/matches/{match_id}/details", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["team_a"]["name"] == "Local security team"
    assert detail.json()["games"] == []
    assert (await client.get("/api/v1/teams/", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/matches/")).status_code == 403
    assert (await client.get("/api/v1/matches/", headers={"X-API-Key": "wrong"})).status_code == 403
    assert (await client.get("/")).json() == {"status": "ok", "message": "Ready"}


@pytest.mark.asyncio
async def test_app_cannot_write_or_trigger_upstream(client, monkeypatch):
    upstream = AsyncMock(return_value=[])
    monkeypatch.setattr(matches, "get_upcoming_matches", upstream)
    for key in (None, "wrong", "local-app-key"):
        headers = {"X-API-Key": key} if key else {}
        assert (await client.post("/api/v1/matches/sync-now", headers=headers)).status_code == 403
        assert (await client.post("/api/v1/teams/", headers=headers, json={"name": "Unauthorized", "game": "CSGO"})).status_code == 403
    upstream.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_is_optional_and_cannot_reuse_app_key(client, monkeypatch):
    for key in ("", "local-app-key"):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", key)
        assert (await client.post("/api/v1/matches/sync-now", headers={"X-API-Key": "local-app-key"})).status_code == 403


@pytest.mark.asyncio
async def test_admin_writes_and_sync_still_work(client, monkeypatch):
    headers = {"X-API-Key": "local-admin-key"}
    created = await client.post("/api/v1/teams/", headers=headers, json={"name": "Authorized local team", "game": "CSGO"})
    assert created.status_code == 200
    for name in ("get_upcoming_matches", "get_running_matches", "get_past_matches"):
        monkeypatch.setattr(matches, name, AsyncMock(return_value=[]))
    synced = await client.post("/api/v1/matches/sync-now", headers=headers)
    assert synced.status_code == 200
    assert synced.json()["partidas_processadas"] == 0


@pytest.mark.asyncio
async def test_system_cache_prevents_parallel_amplification(client, monkeypatch):
    version = {"version": "2.0.0", "download_url": "https://github.com/example", "release_notes": "Local test"}
    version_fetch = AsyncMock(return_value=version)
    health_fetch = AsyncMock(return_value={"status": "healthy", "database": "connected"})
    monkeypatch.setattr(system, "_version_cache", None)
    monkeypatch.setattr(system, "_health_cache", None)
    monkeypatch.setattr(system, "_version_lock", asyncio.Lock())
    monkeypatch.setattr(system, "_health_lock", asyncio.Lock())
    monkeypatch.setattr(system, "_fetch_app_version", version_fetch)
    monkeypatch.setattr(system, "_check_database", health_fetch)
    results = await asyncio.gather(*[client.get("/api/v1/system/app-version") for _ in range(30)])
    assert all(response.json() == version for response in results)
    version_fetch.assert_awaited_once()
    results = await asyncio.gather(*[client.get("/api/v1/system/health") for _ in range(30)])
    assert all(response.status_code == 200 for response in results)
    health_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_uses_local_database(client, monkeypatch):
    monkeypatch.setattr(system, "_health_cache", None)
    monkeypatch.setattr(system, "_health_lock", asyncio.Lock())
    response = await client.get("/api/v1/system/health")
    assert response.json() == {"status": "healthy", "database": "connected"}


@pytest.mark.asyncio
async def test_rate_limits_isolate_clients_and_exempt_health():
    async def endpoint(scope, receive, send):
        from starlette.responses import JSONResponse
        await JSONResponse({"ok": True})(scope, receive, send)
    middleware = RateLimitMiddleware(endpoint)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware, client=("127.0.0.2", 1)), base_url="http://local") as client:
        for _ in range(20):
            assert (await client.post("/api/v1/teams/")).status_code == 200
        response = await client.post("/api/v1/teams/")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        assert (await client.get("/api/v1/matches/")).status_code == 200
        for _ in range(1200):
            response = await client.get("/api/v1/matches/")
        assert response.status_code == 429
        assert (await client.get("/api/v1/system/health")).status_code == 200
        assert (await client.options("/api/v1/matches/")).status_code == 200
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware, client=("127.0.0.3", 1)), base_url="http://local") as other:
        assert (await other.get("/api/v1/matches/")).status_code == 200


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://", "postgresql+asyncpg://"])
@pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full", "disable"])
def test_ssl_policy_and_other_query_options_are_preserved(prefix, mode):
    url, args = database_options(prefix + "user:pass@localhost/test?sslmode=" + mode + "&command_timeout=15")
    assert url.drivername == "postgresql+asyncpg"
    assert args["ssl"] == mode
    assert "sslmode" not in url.query
    assert url.query["command_timeout"] == "15"


def test_remote_connections_require_tls_by_default():
    _, args = database_options("postgresql://user:pass@remote.example/test")
    assert args["ssl"] == "require"
    _, args = database_options("postgresql://user:pass@localhost/test")
    assert "ssl" not in args


@pytest.mark.asyncio
async def test_required_tls_rejects_non_tls_local_server():
    url, args = database_options(str(settings.DATABASE_URL).replace("sslmode=disable", "sslmode=require"))
    tls_engine = create_async_engine(url, connect_args=args)
    try:
        with pytest.raises(Exception, match="SSL"):
            async with tls_engine.connect():
                pass
    finally:
        await tls_engine.dispose()


def test_login_and_registration_removed():
    assert not any("/auth/" in route.path for route in app.routes if hasattr(route, "path"))


@pytest.mark.asyncio
async def test_background_sync_still_updates_local_matches(monkeypatch):
    monkeypatch.setattr(sync_service, "get_team_roster", AsyncMock(return_value=[]))
    payload = {
        "id": 876543210, "status": "running", "begin_at": "2026-10-10T12:00:00Z",
        "tournament": {"tier": "s", "prizepool": "1000"},
        "league": {"id": 87654, "name": "Sync test league"},
        "opponents": [
            {"opponent": {"id": 87651, "name": "Sync team A"}},
            {"opponent": {"id": 87652, "name": "Sync team B"}},
        ],
        "results": [{"team_id": 87651, "score": 1}, {"team_id": 87652, "score": 0}],
        "games": [{"id": 87653, "position": 1, "status": "finished", "winner": {"id": 87651}}],
    }
    try:
        async with SessionLocal() as db:
            await sync_service.sync_matches_to_db([payload], db, "csgo")
            payload["status"] = "finished"
            payload["results"][0]["score"] = 2
            await sync_service.sync_matches_to_db([payload], db, "csgo")
            row = (await db.execute(text("SELECT status, team_a_score FROM matches WHERE pandascore_id=876543210"))).one()
            assert tuple(row) == ("finished", 2)
            assert (await db.execute(text("SELECT count(*) FROM game_maps WHERE id=87653"))).scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_startup_runs_automatic_jobs_without_admin_key(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
    jobs = []
    for name in ("update_live_matches_task", "update_static_matches_task", "resolve_stuck_matches_task"):
        mock = AsyncMock()
        monkeypatch.setattr(main_module, name, mock)
        jobs.append(mock)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
        assert main_module.scheduler.running
        assert len(main_module.scheduler.get_jobs()) == 4
        for job in jobs:
            job.assert_awaited_once()


def test_upgrade_preserves_legacy_users():
    async def seed_and_count(seed=False):
        async with engine.begin() as conn:
            if seed:
                await conn.execute(text("INSERT INTO users (id, username, email) VALUES ('preserved', 'preserved', 'preserved@example.test') ON CONFLICT DO NOTHING"))
            count = (await conn.execute(text("SELECT count(*) FROM users WHERE id='preserved'"))).scalar_one()
        await engine.dispose()
        return count
    asyncio.run(seed_and_count(True))
    config = Config("alembic.ini")
    command.stamp(config, "b5edc4fe6d9a")
    command.upgrade(config, "head")
    assert asyncio.run(seed_and_count()) == 1
    command.check(config)
