from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional 

from app.db.session import get_db
from app.models.match import Match
from app.schemas.match import MatchResponse
from app.services.pandascore import get_upcoming_matches, sync_matches_to_db

router = APIRouter()

@router.get("/", response_model=List[MatchResponse])
async def get_matches(
    limit: int = 50,
    game: Optional[str] = None,   
    status: Optional[str] = None, 
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
        
    query = query.limit(limit)
    result = await db.execute(query)
    
    return result.scalars().all()

@router.post("/sync-now")
async def force_sync(db: AsyncSession = Depends(get_db)):

    matches_data = await get_upcoming_matches(game="csgo", limit=10)
    
    if not matches_data:
        return {"message": "Nenhum dado recebido da API da PandaScore."}
        
    await sync_matches_to_db(matches_data, db, game="csgo")
    
    return {
        "message": "Sincronização concluída", 
        "partidas_processadas": len(matches_data)
    }