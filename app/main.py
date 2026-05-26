from fastapi import FastAPI, Depends 
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.api.v1 import teams, matches
from app.core.security import get_api_key 
from app.db.session import SessionLocal, engine 
from app.models.match import Match               
from app.models.team import Team               
from app.core.logger import logger
from app.services.pandascore import get_upcoming_matches, get_past_matches, sync_matches_to_db

scheduler = AsyncIOScheduler()

async def update_matches_task():
    logger.info("Buscando atualizações")
    
    jogos = ["valorant", "csgo"] 
    
    async with SessionLocal() as db: 
        for jogo in jogos:
            try:
                upcoming_data = await get_upcoming_matches(game=jogo, limit=5)
                if upcoming_data:
                    await sync_matches_to_db(matches_data=upcoming_data, db=db, game=jogo)
                    
                past_data = await get_past_matches(game=jogo, limit=5)
                if past_data:
                    await sync_matches_to_db(matches_data=past_data, db=db, game=jogo)
                    
                logger.info(f"{jogo.upper()} Próximos e Resultados ")
            except Exception as e:
                logger.error(f" Erro ao atualizar {jogo}: {e}")
                
    logger.info(" Todas as atualizações concluídas.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Match.metadata.create_all)
    
    scheduler.add_job(update_matches_task, 'interval', minutes=1)
    scheduler.start()
    
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

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ready"}