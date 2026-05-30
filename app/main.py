import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text, delete, update
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.api.v1 import teams, matches
from app.core.security import get_api_key 
from app.db.session import SessionLocal, engine 
from app.models.match import Match               
from app.models.team import Team               
from app.core.logger import logger
from app.services.pandascore import (
    get_upcoming_matches, 
    get_past_matches, 
    get_running_matches, 
    sync_matches_to_db
)

scheduler = AsyncIOScheduler()

async def update_matches_task():
    logger.info("Buscando atualizações")
    
    jogos = ["valorant", "csgo"] 
    
    async with SessionLocal() as db: 
        for jogo in jogos:
            try:
               
                upcoming_data = await get_upcoming_matches(game=jogo, limit=50)
                if upcoming_data:
                    await sync_matches_to_db(matches_data=upcoming_data, db=db, game=jogo)
                
                
                running_data = await get_running_matches(game=jogo, limit=20)
                if running_data:
                    await sync_matches_to_db(matches_data=running_data, db=db, game=jogo)
                    
               
                past_data = await get_past_matches(game=jogo, limit=50)
                if past_data:
                    await sync_matches_to_db(matches_data=past_data, db=db, game=jogo)
                
                await db.commit() 
                logger.info(f"{jogo.upper()} Próximos, Ao Vivo e Resultados atualizados")
            except Exception as e:
                await db.rollback()
                logger.error(f"Erro crítico ao atualizar {jogo}: {e}", exc_info=True)
                
    logger.info("Todas as atualizações concluídas.")

async def cleanup_old_matches_task():
    logger.info("Iniciando rotina de limpeza (Garbage Collector)...")
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
            
            logger.info(f"Limpeza de banco concluída! {resultado.rowcount} partidas antigas apagadas.")
            
    except Exception as e:
        logger.error(f"Erro crítico na rotina de limpeza: {e}")

async def resolve_stuck_matches_task():
    logger.info("Iniciando Caça-Fantasmas (Procurando jogos travados)...")
    try:
        
        limite_tempo = datetime.now(timezone.utc) - timedelta(minutes=90)
        
        async with SessionLocal() as db:
            stmt = (
                update(Match)
                .where(Match.begin_at < limite_tempo)
                .where(Match.status.in_(["not_started", "running"]))
                .values(status="finished")
            )
            resultado = await db.execute(stmt)
            await db.commit()
            
            if resultado.rowcount > 0:
                logger.info(f"{resultado.rowcount} atualizou para FINALIZADO!")
            else:
                logger.info("atualizado")
                
    except Exception as e:
        logger.error(f"Erro na rotina: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Match.metadata.create_all)
    
    scheduler.add_job(update_matches_task, 'interval', minutes=1)
    scheduler.add_job(cleanup_old_matches_task, 'cron', hour=3, minute=0)
    scheduler.add_job(resolve_stuck_matches_task, 'interval', minutes=30)
    
    scheduler.start()
    
    asyncio.create_task(update_matches_task())
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

@app.get("/api/health", tags=["Health"])
async def health_check():
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"HEALTH CHECK FAILED: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ready"}