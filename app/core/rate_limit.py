import asyncio
import hashlib
from time import monotonic

from fastapi import HTTPException
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.core.config import settings


storage_options = {}
if settings.RATE_LIMIT_STORAGE_URI.startswith(("redis://", "rediss://")):
    storage_options = {"socket_connect_timeout": 2, "socket_timeout": 2}
if settings.RATE_LIMIT_STORAGE_URI.startswith("rediss://"):
    storage_options.update(ssl_cert_reqs="required", ssl_check_hostname=True)
storage = storage_from_string(settings.RATE_LIMIT_STORAGE_URI, **storage_options)
limiter = MovingWindowRateLimiter(storage)
IP_LIMIT = parse("120/minute")
AUTH_IP_LIMIT = parse("10/minute")
ACCOUNT_LIMIT = parse("5/minute")
USER_LIMIT = parse("120/minute")
MAX_BODY_BYTES = 16 * 1024


async def enforce_limit(rule, scope: str, identity: str):
    # Avoid storing raw usernames, email addresses, IPs or tokens in Redis keys.
    key = hashlib.sha256(identity.encode()).hexdigest()
    try:
        allowed = await run_in_threadpool(limiter.hit, rule, "esports", scope, key)
    except Exception:
        # Never silently disable protection when Redis is unavailable.
        raise HTTPException(503, "Proteção de tráfego indisponível", headers={"Retry-After": "60"})
    if not allowed:
        raise HTTPException(429, "Muitas requisições. Tente novamente mais tarde.",
                            headers={"Retry-After": "60"})


class RequestProtectionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Trust only the ASGI peer. Proxy headers must be validated by Uvicorn.
        peer = scope.get("client")
        identity = peer[0] if peer else "unknown"
        try:
            await enforce_limit(IP_LIMIT, "ip", identity)
            if scope["path"].rstrip("/") in {"/api/v1/auth/login", "/api/v1/auth/register"}:
                await enforce_limit(AUTH_IP_LIMIT, "auth-ip", identity)
        except HTTPException as exc:
            return await JSONResponse({"detail": exc.detail}, exc.status_code,
                                      headers=exc.headers)(scope, receive, send)

        # Bound both declared and chunked bodies before parsing JSON/forms.
        body = bytearray()
        deadline = monotonic() + 10
        while True:
            try:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except asyncio.TimeoutError:
                return await JSONResponse({"detail": "Tempo limite de leitura excedido"}, 408)(scope, receive, send)
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                return await JSONResponse({"detail": "Corpo da requisição muito grande"}, 413)(scope, receive, send)
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
