import httpx
import asyncio
from time import monotonic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.db.session import SessionLocal
from app.core.logger import logger

router = APIRouter()

_version_cache = None
_version_expires = 0.0
_version_lock = asyncio.Lock()
_health_cache = None
_health_expires = 0.0
_health_lock = asyncio.Lock()

class AppVersionResponse(BaseModel):
    version: str
    download_url: str
    release_notes: str

@router.get("/app-version", response_model=AppVersionResponse)
async def get_latest_app_version():

    global _version_cache, _version_expires
    async with _version_lock:
        if _version_cache is not None and monotonic() < _version_expires:
            return _version_cache.copy()
        result = await _fetch_app_version()
        _version_cache = result
        _version_expires = monotonic() + 60
        return result.copy()


async def _fetch_app_version():

    github_api_url = "https://api.github.com/repos/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(github_api_url)
            response.raise_for_status() 
            data = response.json()
            latest_version = data.get("tag_name", "").replace("v", "")
            release_notes = data.get("body", "Nova atualização disponível para download!")
            
        except Exception:
            latest_version = "1.0.0"
            release_notes = ""

    return {
        "version": latest_version,
        "download_url": "https://github.com/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest",
        "release_notes": release_notes
    }

@router.get("/health")
async def health_check():
    global _health_cache, _health_expires
    async with _health_lock:
        if _health_cache is not None and monotonic() < _health_expires:
            return _health_cache.copy()
        result = await _check_database()
        _health_cache = result
        _health_expires = monotonic() + 5
        return result.copy()


async def _check_database():
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"HEALTH CHECK FAILED: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
