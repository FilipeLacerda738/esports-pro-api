from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional 

from app.db.session import get_db
from app.models.match import Match
from app.schemas.match import MatchResponse

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