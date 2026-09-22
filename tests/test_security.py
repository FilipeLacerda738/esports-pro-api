import asyncio
import ssl
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import jwt
import pytest
from pydantic import ValidationError

from app.main import app
from app.api.v1 import auth, system
from app.core import rate_limit
from app.core.config import Settings, settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.connection import database_connection_options
from app.db.session import get_db


def override_db(db):
    async def dependency():
        yield db
    app.dependency_overrides[get_db] = dependency


def make_user():
    return SimpleNamespace(
        id=str(uuid4()), username="player", email="player@example.com",
        hashed_password=get_password_hash("long-test-password"),
        avatar_url=None, favorite_team_id=None, created_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize("path", ["/api/v1/teams/", "/api/v1/matches/sync-now"])
def test_mobile_key_cannot_write_or_trigger_sync(client, path):
    response = client.post(path, json={"name": "injected", "game": "CSGO"},
                           headers={"X-API-Key": settings.API_ACCESS_KEY})
    assert response.status_code in {404, 405}


def test_diagnostic_route_is_removed_even_with_mobile_key(client):
    response = client.get("/api/v1/test/pandascore-raw-match/1",
                          headers={"X-API-Key": settings.API_ACCESS_KEY})
    assert response.status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
def test_reads_require_mobile_key(client, headers):
    assert client.get("/api/v1/teams/", headers=headers).status_code == 403


def test_request_limit_cannot_be_bypassed_with_forwarded_header(client):
    for i in range(120):
        assert client.get("/", headers={"X-Forwarded-For": f"192.0.2.{i}"}).status_code == 200
    response = client.get("/")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_limiter_fails_closed(client, monkeypatch):
    def unavailable(*args):
        raise ConnectionError("secret Redis details")
    monkeypatch.setattr(rate_limit.limiter, "hit", unavailable)
    response = client.get("/")
    assert response.status_code == 503
    assert "secret" not in response.text


def test_large_body_is_rejected(client):
    assert client.post("/api/v1/auth/register", content=b"x" * 16385).status_code == 413


def test_body_read_deadline_is_enforced(client, monkeypatch):
    times = iter([100, 111])
    monkeypatch.setattr(rate_limit, "monotonic", lambda: next(times))
    assert client.post("/api/v1/auth/register", content=b"{}").status_code == 408


@pytest.mark.parametrize("origin,allowed", [
    ("https://app.example.com", True), ("https://attacker.example", False),
])
def test_cors_requires_explicit_origin(client, origin, allowed):
    response = client.options("/api/v1/auth/login", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization,Content-Type",
    })
    assert response.status_code == (200 if allowed else 400)
    assert (response.headers.get("Access-Control-Allow-Origin") == origin) == allowed
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.parametrize("changes", [
    {"ENVIRONMENT": "invalid"}, {"API_ACCESS_KEY": ""}, {"SECRET_KEY": "short"},
    {"SECRET_KEY": settings.API_ACCESS_KEY}, {"BACKEND_CORS_ORIGINS": ["*"]},
    {"BACKEND_CORS_ORIGINS": ["https://app.example.com/path"]},
    {"ENVIRONMENT": "production", "DATABASE_SSL": False},
    {"ENVIRONMENT": "production", "DATABASE_SSL": True, "RATE_LIMIT_STORAGE_URI": "memory://"},
    {"DATABASE_URL": "postgresql://u:p@remote.example/db", "DATABASE_SSL": False},
])
def test_insecure_configuration_is_rejected(changes):
    values = settings.model_dump() | changes
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_environment_must_be_explicit(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT")
    values = settings.model_dump()
    values.pop("ENVIRONMENT")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_remote_database_always_verifies_tls_even_with_unsafe_url_parameters():
    config = Settings(_env_file=None, **(settings.model_dump() | {
        "ENVIRONMENT": "production", "DATABASE_SSL": True,
        "DATABASE_URL": "postgresql://user:password@db.example/db?sslmode=disable&ssl=false",
        "RATE_LIMIT_STORAGE_URI": "rediss://cache.example:6379/0",
    }))
    url, args = database_connection_options(config)
    assert "sslmode" not in url.query and "ssl" not in url.query
    assert args["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert args["ssl"].check_hostname is True
    assert args["ssl"].minimum_version >= ssl.TLSVersion.TLSv1_2


def test_login_issues_valid_token_and_me_uses_its_subject(client):
    user = make_user()
    db = AsyncMock()
    db.execute.return_value = Mock(scalars=Mock(return_value=Mock(first=Mock(return_value=user))))
    db.get.return_value = user
    override_db(db)
    response = client.post("/api/v1/auth/login", data={
        "username": user.username, "password": "long-test-password",
    })
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    token = response.json()["access_token"]
    result = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 200
    assert result.json()["id"] == user.id
    assert "hashed_password" not in result.json()


@pytest.mark.parametrize("mutation", ["missing-exp", "expired", "wrong-key", "wrong-audience", "bad-sub", "missing-iat"])
def test_invalid_tokens_are_rejected_before_database_access(client, mutation):
    db = AsyncMock()
    override_db(db)
    payload = jwt.decode(create_access_token({"sub": str(uuid4())}), options={"verify_signature": False})
    key = settings.SECRET_KEY
    if mutation == "missing-exp":
        payload.pop("exp")
    elif mutation == "missing-iat":
        payload.pop("iat")
    elif mutation == "expired":
        payload["exp"] = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
    elif mutation == "wrong-key":
        key = "attacker-signing-key-0000000000000000"
    elif mutation == "wrong-audience":
        payload["aud"] = "another-service"
    else:
        payload["sub"] = "not-a-user-id"
    token = jwt.encode(payload, key, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    db.get.assert_not_awaited()


def test_login_aliases_share_attempt_limit(client):
    user = make_user()
    db = AsyncMock()
    db.execute.return_value = Mock(scalars=Mock(return_value=Mock(first=Mock(return_value=user))))
    override_db(db)
    for i in range(5):
        identity = user.username if i % 2 else user.email
        assert client.post("/api/v1/auth/login", data={"username": identity, "password": "incorrect"}).status_code == 401
    assert client.post("/api/v1/auth/login", data={"username": user.email, "password": "incorrect"}).status_code == 429


def test_password_hashes_remain_compatible():
    stored = get_password_hash("original-password")
    assert verify_password("original-password", stored)
    assert not verify_password("wrong-password", stored)


def test_team_pagination_is_bounded(client):
    db = AsyncMock()
    db.execute.return_value = Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
    override_db(db)
    headers = {"X-API-Key": settings.API_ACCESS_KEY}
    assert client.get("/api/v1/teams/?page=2&limit=20", headers=headers).status_code == 200
    sql = str(db.execute.call_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT 20 OFFSET 20" in sql
    assert client.get("/api/v1/teams/?limit=101", headers=headers).status_code == 422
    assert client.get("/api/v1/teams/?page=10001", headers=headers).status_code == 422


@pytest.mark.asyncio
async def test_version_cache_coalesces_concurrent_requests_and_caches_failures(monkeypatch):
    remote = AsyncMock()
    remote.get.return_value = httpx.Response(200, json={"tag_name": "v2.0.0", "body": "release"},
                                            request=httpx.Request("GET", system.GITHUB_API_URL))
    factory = Mock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=remote)))
    monkeypatch.setattr(system.httpx, "AsyncClient", factory)
    cache = system.VersionCache()
    versions = await asyncio.gather(*(cache.get() for _ in range(10)))
    assert all(v.version == "2.0.0" for v in versions)
    assert remote.get.await_count == 1
    cache.expires_at = 0
    remote.get.side_effect = httpx.ConnectError("private details")
    assert (await cache.get()).version == "2.0.0"
    assert (await cache.get()).version == "2.0.0"
    assert remote.get.await_count == 2
