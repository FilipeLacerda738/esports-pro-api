from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional 
from datetime import date, datetime, time, timezone

from app.db.session import get_db
from app.models.match import Match
from app.schemas.match import MatchResponse
from app.services.pandascore import get_upcoming_matches, sync_matches_to_db, get_running_matches, get_past_matches

router = APIRouter()

@router.get("/", response_model=List[MatchResponse])
async def get_matches(
    limit: int = 50,
    game: Optional[str] = None,   
    status: Optional[str] = None, 
    data_calendario: date = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Match).options(selectinload(Match.league))

    if game:
        query = query.filter(Match.game == game.upper())

    if status:
        query = query.filter(Match.status == status)
        
        if status == "not_started":
            query = query.order_by(Match.begin_at.asc()) 
        else:
            query = query.order_by(Match.begin_at.desc()) 
    else:
        query = query.filter(Match.status != "canceled").order_by(Match.begin_at.desc())
        
    if data_calendario:
        inicio_dia = datetime.combine(data_calendario, time.min, tzinfo=timezone.utc)
        fim_dia = datetime.combine(data_calendario, time.max, tzinfo=timezone.utc)
        query = query.filter(Match.begin_at >= inicio_dia).filter(Match.begin_at <= fim_dia)
        
    query = query.limit(limit)
    result = await db.execute(query)
    
    return result.scalars().all()

@router.post("/sync-now")
async def force_sync(db: AsyncSession = Depends(get_db)):
    jogos = ["csgo", "valorant"]
    total_processado = 0
    
    for jogo in jogos:
        upcoming = await get_upcoming_matches(game=jogo, limit=15)
        running = await get_running_matches(game=jogo, limit=15)
        past = await get_past_matches(game=jogo, limit=15)
        
        if upcoming: 
            await sync_matches_to_db(upcoming, db, game=jogo)
            total_processado += len(upcoming)
            
        if running: 
            await sync_matches_to_db(running, db, game=jogo)
            total_processado += len(running)
            
        if past: 
            await sync_matches_to_db(past, db, game=jogo)
            total_processado += len(past)
    
    return {
        "message": "Manual sync complete", 
        "jogos_verificados": jogos,
        "partidas_processadas": total_processado
    }