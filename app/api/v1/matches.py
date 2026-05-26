from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional 

from app.db.session import get_db
from app.models.match import Match
from app.schemas.match import MatchResponse

router = APIRouter()

@router.get("/", response_model=List[MatchResponse])
async def get_matches(
    limit: int = 10, 
    game: Optional[str] = None,   
    status: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)

):
    query = select(Match).order_by(Match.begin_at.asc())

    if game:
        query = query.filter(Match.game == game.upper())

    if status:
        query = query.filter(Match.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    
    return result.scalars().all()