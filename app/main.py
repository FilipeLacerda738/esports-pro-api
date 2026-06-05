import asyncio
import httpx
import gc  
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text, delete, update, select
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.api.v1 import teams, matches, system, testes
from app.core.security import get_api_key 
from app.db.session import SessionLocal, engine 
from app.db.base import Base
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
from app.models.map import GameMap
from app.core.logger import logger
from app.services.pandascore import (
    get_upcoming_matches, 
    get_past_matches, 
    get_running_matches, 
    sync_matches_to_db,
    get_match_by_id
)

scheduler = AsyncIOScheduler()

async def update_live_matches_task():
    logger.info("Buscando atualizações AO VIVO...")
    jogos = ["valorant", "csgo"] 
    try:
        async with SessionLocal() as db: 
            for jogo in jogos:
                try:
                    running_data = await get_running_matches(game=jogo, limit=15)
                    if running_data:
                        await sync_matches_to_db(matches_data=running_data, db=db, game=jogo)
                    stmt = select(Match).filter(Match.status == "running", Match.game == jogo.upper())
                    result = await db.execute(stmt)
                    running_db = result.scalars().all()

                    if running_db:
                        sniper_data = []
                        for m in running_db:
                            fresh = await get_match_by_id(m.pandascore_id)
                            if fresh:
                                sniper_data.append(fresh)
                        
                        if sniper_data:
                            await sync_matches_to_db(matches_data=sniper_data, db=db, game=jogo)
                    
                    await db.commit() 
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Erro crítico no Live Task ({jogo}): {e}", exc_info=True)
    finally:
        gc.collect()

async def update_static_matches_task():
    logger.info("Sincronizando calendário e resultados...")
    jogos = ["valorant", "csgo"] 
    try:
        async with SessionLocal() as db: 
            for jogo in jogos:
                try:
                    upcoming_data = await get_upcoming_matches(game=jogo, limit=30)
                    if upcoming_data:
                        await sync_matches_to_db(matches_data=upcoming_data, db=db, game=jogo)
                        
                    past_data = await get_past_matches(game=jogo, limit=30)
                    if past_data:
                        await sync_matches_to_db(matches_data=past_data, db=db, game=jogo)
                    
                    await db.commit() 
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Erro crítico no Static Task ({jogo}): {e}", exc_info=True)
    finally:
        gc.collect()

async def cleanup_old_matches_task():
    logger.info("Iniciando limpeza profunda de histórico...")
    try:
        data_limite = datetime.now(timezone.utc) - timedelta(days=10)
        
        async with SessionLocal() as db:
            stmt = (
                delete(Match)
                .where(Match.status == "finished")
                .where(Match.begin_at < data_limite)
            )
            resultado = await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Limpeza de banco concluída: {resultado.rowcount} partidas antigas apagadas.")
            
    except Exception as e:
        logger.error(f"Erro crítico na limpeza profunda: {e}")
    finally:
        gc.collect()

async def resolve_stuck_matches_task():
    logger.info("Iniciando inspeção e resgate de partidas travadas...")
    try:
        now = datetime.now(timezone.utc)
        limite_tempo = now - timedelta(hours=3)
        
        async with SessionLocal() as db:
            stmt_stuck = select(Match).where(
                Match.begin_at < limite_tempo,
                Match.status.in_(["not_started", "running"])
            )
            result = await db.execute(stmt_stuck)
            stuck_matches = result.scalars().all()

            if stuck_matches:
                logger.info(f"Encontradas {len(stuck_matches)} partidas travadas. Fazendo a ÚLTIMA VERIFICAÇÃO na API...")
                sniper_data = []
                
                for match in stuck_matches:
                    fresh_data = await get_match_by_id(match.pandascore_id)
                    if fresh_data:
                        sniper_data.append(fresh_data)
                
                if sniper_data:
                    csgo_data = [d for d in sniper_data if d.get("videogame", {}).get("slug") == "cs-go"]
                    valorant_data = [d for d in sniper_data if d.get("videogame", {}).get("slug") == "valorant"]
                    
                    if csgo_data: await sync_matches_to_db(csgo_data, db, "csgo")
                    if valorant_data: await sync_matches_to_db(valorant_data, db, "valorant")

            stmt_update = (
                update(Match)
                .where(Match.begin_at < limite_tempo)
                .where(Match.status.in_(["not_started", "running"]))
                .values(status="finished")
            )
            res_upd = await db.execute(stmt_update)
            if res_upd.rowcount > 0:
                logger.info(f"{res_upd.rowcount} partidas abandonadas pela API foram finalizadas à força.")

            stmt_delete = (
                delete(Match)
                .where(Match.status.in_(["finished", "canceled"]))
                .where(Match.team_a_score == 0)
                .where(Match.team_b_score == 0)
            )
            res_del = await db.execute(stmt_delete)
            if res_del.rowcount > 0:
                logger.info(f"{res_del.rowcount} jogos (0-0) foram deletados do banco.")
            
            await db.commit()
                
    except Exception as e:
        logger.error(f"Erro na rotina de inspeção: {e}")
    finally:
        gc.collect()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
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
    print("Desligando.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

app.include_router(
    testes.router, 
    prefix="/api/v1/test", 
    tags=["Test"],
    dependencies=[Depends(get_api_key)]
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ready"}