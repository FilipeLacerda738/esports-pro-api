from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.models.team import Team
from app.schemas.team import TeamResponse

router = APIRouter()


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    page: Optional[int] = Query(None, ge=1, le=10000),
    limit: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Team).order_by(Team.id)
    if page is not None or limit is not None:
        effective_page = page or 1
        effective_limit = limit or 50
        query = query.offset((effective_page - 1) * effective_limit).limit(effective_limit)
    result = await db.execute(query)
    return result.scalars().all()
