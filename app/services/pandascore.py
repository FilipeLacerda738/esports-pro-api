import httpx
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.team import Team
from app.models.match import Match
from app.models.league import League 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.pandascore.co"

async def get_upcoming_matches(game: str = "csgo", limit: int = 5):
    url = f"{BASE_URL}/{game}/matches/upcoming"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.PANDASCORE_API_KEY}"
    }
    
    params = {
        "sort": "begin_at",
        "per_page": limit
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Buscando as próximas {limit} partidas de {game.upper()}...")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status() 
            data = response.json()
            logger.info(f"Sucesso! Encontradas {len(data)} partidas na API.")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro na API da PandaScore. Status: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Erro de conexão: {e}")
            return []

async def sync_matches_to_db(matches_data: list, db: AsyncSession, game: str):
    for data in matches_data:
        opponents = data.get("opponents", [])
        if len(opponents) != 2:
            continue

        league_info = data.get("league")
        league_id = None
        
        if league_info:
            league_id = league_info.get("id")
            result_league = await db.execute(select(League).filter(League.id == league_id))
            league = result_league.scalars().first()
            
            if not league:
                league = League(
                    id=league_id,
                    name=league_info.get("name", "Desconhecido"),
                    image_url=league_info.get("image_url")
                )
                db.add(league)
                await db.flush() 
            else:
                if league_info.get("image_url"):
                    league.image_url = league_info.get("image_url")

        team_a_info = opponents[0]["opponent"]
        team_b_info = opponents[1]["opponent"]
  
        result_a = await db.execute(select(Team).filter(Team.name == team_a_info["name"]))
        team_a = result_a.scalars().first()
        if not team_a:
            team_a = Team(
                name=team_a_info["name"], 
                acronym=team_a_info.get("acronym"), 
                image_url=team_a_info.get("image_url"), 
                game=game.upper()
            )
            db.add(team_a)
            await db.flush()
   
        result_b = await db.execute(select(Team).filter(Team.name == team_b_info["name"]))
        team_b = result_b.scalars().first()
        if not team_b:
            team_b = Team(
                name=team_b_info["name"], 
                acronym=team_b_info.get("acronym"), 
                image_url=team_b_info.get("image_url"), 
                game=game.upper()
            )
            db.add(team_b)
            await db.flush()
      
        begin_at = None
        if data.get("begin_at"):
            begin_at = datetime.fromisoformat(data["begin_at"].replace('Z', '+00:00'))

        score_a = 0
        score_b = 0
        for result in data.get("results", []):
            if result["team_id"] == team_a_info["id"]: score_a = result["score"]
            if result["team_id"] == team_b_info["id"]: score_b = result["score"]
    
        pandascore_id = data["id"]
        result_match = await db.execute(select(Match).filter(Match.pandascore_id == pandascore_id))
        match = result_match.scalars().first()
        
        if not match:
            match = Match(
                pandascore_id=pandascore_id,
                game=game.upper(),
                status=data["status"],
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                team_a_score=score_a,
                team_b_score=score_b,
                begin_at=begin_at,
                league_id=league_id 
            )
            db.add(match)
        else:
            match.status = data["status"]
            match.team_a_score = score_a
            match.team_b_score = score_b
            match.begin_at = begin_at
            match.league_id = league_id 
            
async def get_past_matches(game: str = "csgo", limit: int = 5):
    url = f"{BASE_URL}/{game}/matches/past"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.PANDASCORE_API_KEY}"
    }
    
    params = {
        "sort": "-begin_at",
        "per_page": limit
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Buscando os últimos {limit} resultados de {game.upper()}...")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status() 
            data = response.json()
            logger.info(f"Sucesso! Encontrados {len(data)} resultados antigos na API.")
            return data
            
        except Exception as e:
            logger.error(f"Erro ao buscar resultados passados: {e}")
            return []