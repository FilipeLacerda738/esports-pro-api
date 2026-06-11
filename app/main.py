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
from app.api.v1 import teams, matches, system, testes
from app.core.security import get_api_key 
from app.core.logger import logger

from app.jobs.tasks import (
    update_live_matches_task,
    update_static_matches_task,
    cleanup_old_matches_task,
    resolve_stuck_matches_task
)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(update_live_matches_task, 'interval', minutes=1)
    scheduler.add_job(update_static_matches_task, 'interval', minutes=30)
    scheduler.add_job(cleanup_old_matches_task, 'cron', hour=5, minute=0)
    scheduler.add_job(resolve_stuck_matches_task, 'interval', minutes=30)
    
    scheduler.start()
    
    asyncio.create_task(update_live_matches_task())
    asyncio.create_task(update_static_matches_task())
    asyncio.create_task(resolve_stuck_matches_task())
    
    yield 

    scheduler.shutdown()
    logger.info("Desligando e encerrando agendador.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

origins = getattr(settings, "BACKEND_CORS_ORIGINS", ["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

if getattr(settings, "ENVIRONMENT", "production") == "development":
    app.include_router(
        testes.router, 
        prefix="/api/v1/test", 
        tags=["Test (Dev Only)"],
        dependencies=[Depends(get_api_key)]
    )
    logger.info("Rotas de Debug habilitadas para ambiente de desenvolvimento.")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ready"}