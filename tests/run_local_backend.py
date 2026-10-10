import asyncio
import os
from pathlib import Path
import subprocess
import sys
import time
import socket
import ssl
import struct
from urllib.parse import quote

import asyncpg
from dotenv import dotenv_values
import httpx


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:58081"
LOCAL_DSN = "postgresql://postgres:local-security-test-only@127.0.0.1:55439/esports_security_test?sslmode=require"
LOCAL_BACKEND_DSN = "postgresql+asyncpg://esports_backend:local-backend-test-only@127.0.0.1:55439/esports_security_test?sslmode=require"
LOCAL_CA = Path(os.environ['LOCALAPPDATA']) / 'EsportsSecurityPostgres' / 'data' / 'server.crt'
LOCAL_DSN = LOCAL_DSN.replace('sslmode=require', 'sslmode=verify-full&sslrootcert=' + quote(LOCAL_CA.as_posix(), safe=''))
LOCAL_BACKEND_DSN = LOCAL_BACKEND_DSN.replace('sslmode=require', 'sslmode=verify-full&sslrootcert=' + quote(LOCAL_CA.as_posix(), safe=''))


def check_local_tls():
    verified = ssl.create_default_context(cafile=str(LOCAL_CA))
    def handshake(context, hostname):
        with socket.create_connection(('127.0.0.1', 55439), timeout=5) as connection:
            connection.sendall(struct.pack('!II', 8, 80877103))
            assert connection.recv(1) == b'S'
            with context.wrap_socket(connection, server_hostname=hostname) as secured:
                assert secured.version() in ('TLSv1.2', 'TLSv1.3')
    handshake(verified, 'localhost')
    for context, hostname in ((verified, 'wrong.local'), (ssl.create_default_context(), 'localhost')):
        try:
            handshake(context, hostname)
        except ssl.SSLCertVerificationError:
            continue
        raise AssertionError('Invalid certificate or hostname was accepted')
    print('Local TLS: valid CA accepted, wrong hostname and untrusted CA rejected: PASS', flush=True)


async def prepare_local_data():
    conn = await asyncpg.connect(LOCAL_DSN)
    try:
        assert await conn.fetchval("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
        await conn.execute(
            "UPDATE matches SET status='not_started', begin_at=now()+interval '2 days' "
            "WHERE pandascore_id=987654321"
        )
    finally:
        await conn.close()


async def check_http(api_key):
    headers = {"X-API-Key": api_key}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        assert (await client.get("/")).json() == {"status": "ok", "message": "Ready"}
        assert (await client.get("/api/v1/system/health")).json() == {"status": "healthy", "database": "connected"}
        response = await client.get("/api/v1/matches/", headers=headers, params={"game": "csgo", "limit": 15, "page": 1})
        assert response.status_code == 200
        assert set(response.json()) == {"total", "page", "size", "has_more", "items"}
        assert any(row["pandascore_id"] == 987654321 for row in response.json()["items"])
        detail = await client.get("/api/v1/matches/987654321/details", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["team_a"]["name"] == "Local security team"
        assert (await client.get("/api/v1/teams/", headers=headers)).status_code == 200
        assert (await client.get("/api/v1/matches/")).status_code == 403
        assert (await client.post("/api/v1/matches/sync-now", headers=headers)).status_code == 403
        assert (await client.post("/api/v1/teams/", headers=headers, json={"name": "Denied", "game": "CSGO"})).status_code == 403
        assert (await client.post("/api/v1/auth/login")).status_code == 404
        assert (await client.post("/api/v1/auth/register")).status_code == 404
        assert (await client.get("/api/v1/test/pandascore-raw-match/123", headers=headers)).status_code == 404
        version = await client.get("/api/v1/system/app-version")
        assert version.status_code == 200
        assert set(version.json()) == {"version", "download_url", "release_notes"}
        concurrent = await asyncio.gather(*[client.get("/api/v1/matches/", headers=headers) for _ in range(50)])
        assert all(response.status_code == 200 for response in concurrent)
    print("HTTP acceptance: app routes, existing key, blocked writes, removed accounts, 50 concurrent reads: PASS", flush=True)


async def check_limits_and_health():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        responses = [await client.get("/api/v1/system/app-version") for _ in range(1201)]
        assert all(response.status_code in (200, 429) for response in responses)
        assert any(response.status_code == 429 for response in responses)
        response = await client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert (await client.get("/")).status_code == 200
    print("HTTP acceptance: rate limit and health availability: PASS", flush=True)


def main():
    check_local_tls()
    values = dotenv_values(ROOT / ".env")
    api_key = values.get("API_ACCESS_KEY")
    keys = [key.strip() for key in (values.get("PANDASCORE_KEYS") or values.get("PANDASCORE_API_KEY") or "").split(",") if key.strip()]
    if not api_key or not keys:
        raise RuntimeError("Local .env must contain the authorized app and PandaScore keys")
    selected = keys[2] if len(keys) >= 3 else keys[0]
    task_env = dict(os.environ)
    task_env.update(
        DATABASE_URL=LOCAL_BACKEND_DSN, MIGRATION_DATABASE_URL="",
        API_ACCESS_KEY=api_key, ADMIN_API_KEY="", ENVIRONMENT="production",
        PANDASCORE_API_KEY=selected, PANDASCORE_KEYS=selected,
        PYTHONUTF8="1",
    )
    asyncio.run(prepare_local_data())
    log_path = ROOT / "logs" / "local-backend-acceptance.log"
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "58081", "--workers", "1"],
            cwd=ROOT, env=task_env, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Local backend exited before becoming ready; see local log")
                try:
                    if httpx.get(BASE_URL + "/", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("Local backend did not become ready")
            print("Real Uvicorn startup with local PostgreSQL TLS and PandaScore key " + str(3 if len(keys) >= 3 else 1) + ": PASS", flush=True)
            asyncio.run(check_http(api_key))
            time.sleep(65)
            asyncio.run(check_limits_and_health())
            log.flush()
            raw_log = log_path.read_bytes()
            try:
                content = raw_log.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_log.decode("cp1252")
            assert "Buscando atualizações AO VIVO" in content
            assert content.count("Buscando atualizações AO VIVO") >= 2
            assert "Sincronizando calendário e resultados" in content
            assert "Iniciando inspeção e resgate" in content
            failures = ("Erro crítico", "Erro na rotina de inspeção", "Task exception was never retrieved", "Exception in ASGI application", "TODAS as chaves", "Traceback")
            assert not any(marker in content for marker in failures), "Local runtime logged a job or server failure"
            print("Automatic startup jobs and one scheduled live cycle: PASS", flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
