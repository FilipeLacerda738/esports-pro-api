"""Limites locais para a instancia unica, sem depender de Redis externo."""
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from starlette.responses import JSONResponse


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self.limiter = FixedWindowRateLimiter(MemoryStorage())
        self.read_limit = parse("1200/minute")
        self.write_limit = parse("20/minute")
        self.global_limit = parse("12000/minute")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/api/v1/"):
            # Health checks nao podem causar falha no deploy por rate limiting.
            if scope["path"] != "/api/v1/system/health" and scope["method"] != "OPTIONS":
                client = scope.get("client")
                identity = client[0] if client else "unknown"
                limit = self.read_limit if scope["method"] in ("GET", "HEAD") else self.write_limit
                if (not self.limiter.hit(limit, identity)
                        or not self.limiter.hit(self.global_limit, "all")):
                    response = JSONResponse(
                        {"detail": "Too many requests"}, status_code=429,
                        headers={"Retry-After": "60"},
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)
