"""Esports Hub - Plataforma de acompanhamento de e-sports
Copyright (C) 2026 George Filipe Rodrigues de Lacerda

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""

import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.api.v1 import auth, teams, matches, system
from app.core.security import get_api_key 
from app.core.logger import logger
from app.core.rate_limit import RequestProtectionMiddleware, storage
from starlette.concurrency import run_in_threadpool

from app.jobs.tasks import (
    update_live_matches_task,
    update_static_matches_task,
    cleanup_old_matches_task,
    resolve_stuck_matches_task
)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await run_in_threadpool(storage.check):
        raise RuntimeError("Rate limit storage is unavailable")
    scheduler.add_job(update_live_matches_task, 'interval', minutes=1)
    scheduler.add_job(update_static_matches_task, 'interval', minutes=45)
    scheduler.add_job(cleanup_old_matches_task, 'cron', hour=6, minute=30)
    scheduler.add_job(resolve_stuck_matches_task, 'interval', minutes=45)
    
    scheduler.start()
    
    asyncio.create_task(update_live_matches_task())
    asyncio.create_task(update_static_matches_task())
    asyncio.create_task(resolve_stuck_matches_task())
    
    yield 

    scheduler.shutdown()
    logger.info("Desligando e encerrando agendador.")

app = FastAPI(
    title=settings.PROJECT_NAME, lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
)

app.add_middleware(RequestProtectionMiddleware)
origins = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.include_router(
    teams.router, 
    prefix="/api/v1/teams", 
    tags=["Teams"],
    dependencies=[Depends(get_api_key)] 
)

app.include_router(
    matches.router, 
    prefix="/api/v1/matches", 
    tags=["Matches"],
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    system.router, 
    prefix="/api/v1/system", 
    tags=["System"]
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ready"}
