import asyncio
from time import monotonic

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import text

from app.db.session import SessionLocal
from app.core.logger import logger

router = APIRouter()
GITHUB_API_URL = "https://api.github.com/repos/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest"
DOWNLOAD_URL = "https://github.com/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest"


class AppVersionResponse(BaseModel):
    version: str
    download_url: str
    release_notes: str


class VersionCache:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.expires_at = 0.0
        self.value = AppVersionResponse(version="1.0.0", download_url=DOWNLOAD_URL, release_notes="")

    async def get(self):
        if monotonic() < self.expires_at:
            return self.value
        async with self.lock:
            if monotonic() < self.expires_at:
                return self.value
            ttl = 300
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(GITHUB_API_URL)
                    response.raise_for_status()
                    data = response.json()
                    self.value = AppVersionResponse(
                        version=data["tag_name"].removeprefix("v"),
                        download_url=DOWNLOAD_URL,
                        release_notes=data.get("body") or "",
                    )
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, ValidationError):
                ttl = 60  # Cache failures too, retaining the last successful value.
                logger.warning("Não foi possível atualizar a versão do aplicativo")
            self.expires_at = monotonic() + ttl
            return self.value


version_cache = VersionCache()


@router.get("/app-version", response_model=AppVersionResponse)
async def get_latest_app_version():
    return await version_cache.get()


@router.get("/health")
async def health_check():
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"HEALTH CHECK FAILED: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")