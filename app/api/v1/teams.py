from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.session import get_db
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamResponse

router = APIRouter()


@router.post("/", response_model=TeamResponse)
async def create_team(team: TeamCreate, db: AsyncSession = Depends(get_db)):
  
    novo_time = Team(**team.model_dump())
    
    db.add(novo_time)
    await db.commit()         
    await db.refresh(novo_time) 
    
    return novo_time


@router.get("/", response_model=List[TeamResponse])
async def list_teams(db: AsyncSession = Depends(get_db)):

    resultado = await db.execute(select(Team))
    times = resultado.scalars().all()
    return times