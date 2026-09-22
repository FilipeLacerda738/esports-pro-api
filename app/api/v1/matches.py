from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import date, datetime, time, timezone

from app.db.session import get_db
from app.models.match import Match
from app.models.team import Team
from app.schemas.match import MatchResponse, MatchDetailResponse, PaginatedMatchResponse

router = APIRouter()

@router.get("/", response_model=PaginatedMatchResponse)
async def get_matches(
    page: int = Query(1, ge=1, le=10000, description="Número da página, deve ser maior ou igual a 1"),
    limit: int = Query(15, ge=1, le=100, description="Quantidade de itens por página (máximo 100)"),
    game: Optional[str] = Query(None, max_length=50),
    status: Optional[str] = Query(None, max_length=30),
    tier: Optional[str] = Query(None, pattern=r"^[SsAaBbCcDd]$", max_length=1),
    data_calendario: date = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Match)

    if game:
        query = query.filter(Match.game == game.upper())

    if tier:
        query = query.filter(Match.tier.ilike(tier))

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

    count_query = query.with_only_columns(func.count(Match.id)).order_by(None)
    total_result = await db.execute(count_query)
    total_items = total_result.scalar()

    offset = (page - 1) * limit

    query = query.options(selectinload(Match.league)).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedMatchResponse(
        total=total_items,
        page=page,
        size=len(items),
        has_more=(offset + len(items)) < total_items,
        items=items
    )

@router.get("/{match_id}/details", response_model=MatchDetailResponse)
async def get_match_details(match_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Match)
        .options(
            selectinload(Match.league),
            selectinload(Match.team_a).selectinload(Team.players),
            selectinload(Match.team_b).selectinload(Team.players),
            selectinload(Match.games)
        )
        .where(or_(Match.id == match_id, Match.pandascore_id == match_id))
    )

    result = await db.execute(stmt)
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Partida não encontrada no banco de dados.")

    return match
