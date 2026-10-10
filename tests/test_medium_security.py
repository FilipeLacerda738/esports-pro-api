import asyncio
import ipaddress
import ssl
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal, engine
from app.db.connection import database_options
from app.core.proxy import client_identity
from app.core.resources import ResourceLimitMiddleware
from app.core.synchronization import serialized_sync
from app.models.match import Match
from app.jobs import tasks
from app.api.v1 import system
from app.services.pandascore import sync
from reset_db import is_local_database


@pytest.mark.parametrize('host', ['localhost', '127.0.0.1', '[::1]'])
def test_reset_accepts_loopback(host):
    assert is_local_database(f'postgresql://user:pass@{host}/test')


@pytest.mark.parametrize('url', [
    'postgresql://user:pass@remote.example/test',
    'postgresql://user:pass@localhost.remote.example/test',
    'postgresql://user:pass@10.0.0.1/test',
    'postgresql://user:pass@localhost/test?host=remote.example',
    'postgresql:///test', 'not-a-url',
])
def test_reset_rejects_remote_or_overrides(url):
    assert not is_local_database(url)


def test_verified_tls_context():
    url, options = database_options('postgresql://u:p@aws-1-sa-east-1.pooler.supabase.com/db?sslmode=verify-full&sslrootcert=security/supabase-ca.crt')
    context = options['ssl']
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert 'sslrootcert' not in url.query
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_ca_requires_hostname_verification():
    with pytest.raises(ValueError):
        database_options('postgresql://u:p@localhost/db?sslmode=require&sslrootcert=security/supabase-ca.crt')


@pytest.mark.parametrize('query', ['', '?sslmode=require', '?sslmode=disable'])
def test_supabase_automatically_verifies_existing_connections(query):
    _, options = database_options('postgresql://u:p@aws-1-sa-east-1.pooler.supabase.com/db' + query)
    assert options['ssl'].verify_mode == ssl.CERT_REQUIRED
    assert options['ssl'].check_hostname


@pytest.mark.parametrize('peer,header,expected', [
    ('8.8.8.8', '1.1.1.1', '8.8.8.8'),
    ('10.0.0.1', '1.1.1.1, 8.8.8.8, 10.0.0.2', '8.8.8.8'),
    ('10.0.0.1', 'malformed', '10.0.0.1'),
    ('10.0.0.1', '10.0.0.2', '10.0.0.1'),
    ('10.0.0.1', '2001:4860:4860::8888', '2001:4860:4860::8888'),
])
def test_proxy_identity_ignores_spoofed_prefix(peer, header, expected):
    scope = {'client': (peer, 1), 'headers': [(b'x-forwarded-for', header.encode())]}
    assert client_identity(scope, (ipaddress.ip_network('10.0.0.0/8'),)) == expected


@pytest.mark.asyncio
async def test_all_sync_jobs_are_serialized():
    active = 0
    maximum = 0
    @serialized_sync
    async def job():
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
    await asyncio.gather(*[job() for _ in range(8)])
    assert maximum == 1
    for name in ('update_live_matches_task', 'update_static_matches_task', 'cleanup_old_matches_task', 'resolve_stuck_matches_task'):
        assert hasattr(getattr(tasks, name), '__wrapped__')


@pytest.mark.asyncio
@pytest.mark.parametrize('fresh', [None, {}, {'id': -1, 'status': 'finished'}])
async def test_failed_lookup_never_finalizes_or_deletes(fresh, monkeypatch):
    monkeypatch.setattr(tasks, 'get_match_by_id', AsyncMock(return_value=fresh))
    try:
        async with SessionLocal() as db:
            match = Match(pandascore_id=765432101, game='CSGO', status='running', begin_at=datetime.now(timezone.utc)-timedelta(hours=4), team_a_score=0, team_b_score=0)
            db.add(match)
            await db.commit()
            match_id = match.id
        await tasks.resolve_stuck_matches_task()
        async with SessionLocal() as db:
            found = await db.get(Match, match_id)
            assert found is not None and found.status == 'running'
            await db.delete(found)
            await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_health_failure_is_cached(monkeypatch):
    check = AsyncMock(side_effect=HTTPException(status_code=500, detail='test'))
    monkeypatch.setattr(system, '_check_database', check)
    monkeypatch.setattr(system, '_health_lock', asyncio.Lock())
    monkeypatch.setattr(system, '_health_cache', None)
    monkeypatch.setattr(system, '_health_error', None)
    monkeypatch.setattr(system, '_health_expires', 0)
    async def request():
        with pytest.raises(HTTPException) as error:
            await system.health_check()
        assert error.value.status_code == 503
    await asyncio.gather(*[request() for _ in range(20)])
    check.assert_awaited_once()


@pytest.mark.asyncio
async def test_resource_limits_and_reserved_health():
    from starlette.responses import JSONResponse
    entered = asyncio.Event()
    release = asyncio.Event()
    async def endpoint(scope, receive, send):
        if scope['path'] == '/api/v1/block':
            entered.set()
            await release.wait()
        if scope['path'] == '/api/v1/body':
            while (await receive()).get('more_body'):
                pass
        await JSONResponse({'value': 'x'*200 if scope['path'] == '/api/v1/large' else 'ok'})(scope, receive, send)
    limited = ResourceLimitMiddleware(endpoint, max_concurrent=1, max_body=32, max_response=100)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=limited), base_url='http://local') as client:
        pending = asyncio.create_task(client.get('/api/v1/block'))
        await entered.wait()
        assert (await client.get('/api/v1/read')).status_code == 503
        assert (await client.get('/api/v1/system/health')).status_code == 200
        release.set()
        assert (await pending).status_code == 200
        assert (await client.post('/api/v1/body', content=b'x'*33)).status_code == 413
        async def chunks():
            yield b'x'*20
            yield b'x'*20
        assert (await client.post('/api/v1/body', content=chunks())).status_code == 413
        assert (await client.get('/api/v1/large')).status_code == 503
        assert (await client.get('/api/v1/read?x='+'x'*8193)).status_code == 414
        assert (await client.get('/api/v1/read')).status_code == 200
    assert limited.active == 0


@pytest.mark.asyncio
async def test_bounded_queries_preserve_list_shape():
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local', headers={'X-API-Key': 'local-app-key'}) as client:
            assert (await client.get('/api/v1/matches/?page=100000000')).status_code == 422
            assert (await client.get('/api/v1/matches/?page=10000&limit=100')).status_code == 422
            assert (await client.get('/api/v1/teams/?limit=5001')).status_code == 422
            result = await client.get('/api/v1/teams/?limit=1')
            assert result.status_code == 200 and isinstance(result.json(), list)
            assert len(result.json()) <= 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_sessions_keep_orm_objects_local(monkeypatch):
    monkeypatch.setattr(sync, 'get_team_roster', AsyncMock(return_value=[]))
    payload = {
        'id': 765432102, 'status': 'running', 'tournament': {'tier': 's'},
        'league': {'id': 765432103, 'name': 'Concurrent league'},
        'opponents': [
            {'opponent': {'id': 765432104, 'name': 'Concurrent A'}},
            {'opponent': {'id': 765432105, 'name': 'Concurrent B'}},
        ],
        'results': [{'team_id': 765432104, 'score': 1}],
    }
    async def run():
        async with SessionLocal() as db:
            await sync.sync_matches_to_db([payload], db, 'csgo')
    try:
        await asyncio.gather(run(), run(), run())
        async with SessionLocal() as db:
            rows = (await db.execute(select(Match).where(Match.pandascore_id == 765432102))).scalars().all()
            assert len(rows) == 1 and rows[0].team_a_score == 1
            await db.delete(rows[0])
            await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('status,score,deleted', [('running', 0, False), ('finished', 2, False), ('canceled', 0, True)])
async def test_rescue_only_applies_confirmed_status(status, score, deleted, monkeypatch):
    old_time = datetime.now(timezone.utc)-timedelta(hours=4)
    payload = {
        'id': 765432106, 'status': status, 'begin_at': old_time.isoformat(),
        'videogame': {'slug': 'cs-go'}, 'tournament': {'tier': 's'},
        'league': {'id': 765432103, 'name': 'Concurrent league'},
        'opponents': [
            {'opponent': {'id': 765432104, 'name': 'Concurrent A'}},
            {'opponent': {'id': 765432105, 'name': 'Concurrent B'}},
        ],
        'results': [{'team_id': 765432104, 'score': score}, {'team_id': 765432105, 'score': 0}],
    }
    monkeypatch.setattr(tasks, 'get_match_by_id', AsyncMock(return_value=payload))
    monkeypatch.setattr(sync, 'get_team_roster', AsyncMock(return_value=[]))
    try:
        async with SessionLocal() as db:
            match = Match(pandascore_id=payload['id'], game='CSGO', status='running', begin_at=old_time, team_a_score=0, team_b_score=0)
            db.add(match)
            await db.commit()
            match_id = match.id
        await tasks.resolve_stuck_matches_task()
        async with SessionLocal() as db:
            found = await db.get(Match, match_id)
            if deleted:
                assert found is None
            else:
                assert found is not None and found.status == status and found.team_a_score == score
                await db.delete(found)
                await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_chunked_body_is_rejected_by_real_app():
    async def chunks():
        yield b'{"name":"'
        yield b'x'*65537
        yield b'","game":"CSGO"}'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local') as client:
        response = await client.post('/api/v1/teams/', content=chunks(), headers={'X-API-Key': 'local-admin-key', 'Content-Type': 'application/json'})
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_body_timeout_releases_capacity():
    async def receive():
        await asyncio.sleep(10)
    async def endpoint(scope, receive, send):
        await receive()
    messages = []
    async def send(message):
        messages.append(message)
    limited = ResourceLimitMiddleware(endpoint, body_timeout=0.001)
    scope = {'type': 'http', 'path': '/api/v1/body', 'method': 'POST', 'headers': []}
    await limited(scope, receive, send)
    assert messages[0]['status'] == 408
    assert limited.active == 0
