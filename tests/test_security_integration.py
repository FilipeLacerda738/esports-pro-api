import asyncio
import ssl

import httpx
import pytest
import trustme
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import Settings, settings
from app.core.security import verify_password
from app.db.base import Base
from app.db.connection import database_connection_options
from app.db.session import get_db
from app.models.team import Team
from app.models.user import User


@pytest.mark.asyncio
async def test_registration_login_and_profile_isolation_with_database(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "security.db").as_posix())
    sessions = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def database():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = database
    try:
        async with sessions() as session:
            session.add(Team(name="Legitimate team", game="CSGO"))
            await session.commit()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            users = []
            for name in ("alice", "bob"):
                result = await client.post("/api/v1/auth/register", json={
                    "username": name, "email": f"{name}@example.com", "password": "long-test-password",
                })
                assert result.status_code == 201, result.text
                assert "hashed_password" not in result.json()
                users.append(result.json())
            duplicate = await client.post("/api/v1/auth/register", json={
                "username": "alice", "email": "alice@example.com", "password": "long-test-password",
            })
            assert duplicate.status_code == 400
            login = await client.post("/api/v1/auth/login", data={
                "username": "bob@example.com", "password": "long-test-password",
            })
            assert login.status_code == 200
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            result = await client.put("/api/v1/auth/profile/team", headers=headers,
                                      json={"favorite_team_id": 1, "user_id": users[0]["id"]})
            assert result.status_code == 200
            assert result.json()["id"] == users[1]["id"]
            assert result.json()["favorite_team_id"] == 1
            missing = await client.put("/api/v1/auth/profile/team", headers=headers,
                                       json={"favorite_team_id": 999})
            assert missing.status_code == 404
            assert (await client.get("/api/v1/auth/me", headers=headers)).json()["id"] == users[1]["id"]
        async with sessions() as session:
            alice = await session.get(User, users[0]["id"])
            assert alice.favorite_team_id is None
            assert alice.hashed_password != "long-test-password"
            assert verify_password("long-test-password", alice.hashed_password)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_chunked_request_cannot_bypass_body_limit():
    async def chunks():
        yield b"x" * 9000
        yield b"y" * 9000
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", content=chunks())
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_database_tls_context_rejects_untrusted_ca_and_wrong_hostname(tmp_path):
    ca = trustme.CA()
    certificate = ca.issue_cert("db.example")
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certificate.configure_cert(server_context)
    ca_path = tmp_path / "ca.pem"
    ca.cert_pem.write_to_path(ca_path)

    async def handle(reader, writer):
        writer.write(b"ok")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 0, ssl=server_context)
    port = server.sockets[0].getsockname()[1]
    values = settings.model_dump() | {"DATABASE_SSL": True, "DATABASE_CA_FILE": None}
    untrusted = database_connection_options(Settings(_env_file=None, **values))[1]["ssl"]
    values["DATABASE_CA_FILE"] = str(ca_path)
    trusted = database_connection_options(Settings(_env_file=None, **values))[1]["ssl"]
    try:
        with pytest.raises(ssl.SSLCertVerificationError):
            await asyncio.open_connection("127.0.0.1", port, ssl=untrusted, server_hostname="db.example")
        with pytest.raises(ssl.SSLCertVerificationError):
            await asyncio.open_connection("127.0.0.1", port, ssl=trusted, server_hostname="attacker.example")
        reader, writer = await asyncio.open_connection("127.0.0.1", port, ssl=trusted, server_hostname="db.example")
        assert await reader.read() == b"ok"
        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()
