import os
import httpx
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.logger import logger
from app.core.config import settings
from app.models.team import Team
from app.models.match import Match
from app.models.league import League 
from app.models.map import GameMap
from app.models.player import Player

BASE_URL = "https://api.pandascore.co"

API_KEYS_STR = settings.PANDASCORE_KEYS if settings.PANDASCORE_KEYS else settings.PANDASCORE_API_KEY
API_KEYS = [k.strip() for k in API_KEYS_STR.split(",") if k.strip()]

async def request_pandascore(endpoint: str, params: dict = None):
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{BASE_URL}/{endpoint}"
    headers = {"Accept": "application/json"}
    
    if not API_KEYS:
        logger.error("Nenhuma chave da PandaScore encontrada nas configurações!")
        return None

    async with httpx.AsyncClient() as client:
        for i, key in enumerate(API_KEYS):
            headers["Authorization"] = f"Bearer {key}"
            try:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 429:
                    logger.warning(f"Chave {i+1}/{len(API_KEYS)} estourou (429). Tentando chave reserva...")
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f" Chave {i+1}/{len(API_KEYS)} estourou (429). Tentando chave reserva...")
                    continue
                logger.error(f"Erro HTTP na PandaScore: {e.response.status_code}")
                return None
            except Exception as e:
                logger.error(f"Erro de conexão com a PandaScore: {e}")
                return None
                
        logger.critical("TODAS as chaves da PandaScore falharam")
        return None


async def get_team_roster(team_id: int, game: str):
    data = await request_pandascore(f"/teams/{team_id}")
    return data.get("players", []) if data else []

async def sync_team_players(team_id_pandascore: int, team_id_db: int, game: str, db: AsyncSession):
    stmt = select(Player).filter(Player.team_id == team_id_db)
    result = await db.execute(stmt)
    existing_players = result.scalars().all()
    
    if existing_players:
        return
        
    logger.info(f"Buscando elenco do time ID {team_id_pandascore} na PandaScore...")
    players_data = await get_team_roster(team_id_pandascore, game)
    
    for p_data in players_data:
        p_id = p_data.get("id")
        
        res_p = await db.execute(select(Player).filter(Player.id == p_id))
        player = res_p.scalars().first()
        
        if not player:
            player = Player(
                id=p_id,
                name=p_data.get("name"),
                first_name=p_data.get("first_name"),
                last_name=p_data.get("last_name"),
                image_url=p_data.get("image_url"),
                team_id=team_id_db
            )
            db.add(player)
        else:
            player.team_id = team_id_db
            player.image_url = p_data.get("image_url")

async def get_upcoming_matches(game: str = "csgo", limit: int = 5):
    logger.info(f"Buscando as próximas {limit} partidas de {game.upper()}...")
    params = {"sort": "begin_at", "per_page": limit}
    data = await request_pandascore(f"/{game}/matches/upcoming", params=params)
    if data:
        logger.info(f"Encontradas {len(data)} partidas na API.")
        return data
    return []

async def sync_matches_to_db(matches_data: list, db: AsyncSession, game: str):
    for data in matches_data:
        tournament_info = data.get("tournament") or {}
        tier = tournament_info.get("tier")
        if str(tier).lower() not in ["s", "a", "b"]:
            continue

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
            
        if team_a_info.get("players"):
            for p_data in team_a_info.get("players", []):
                p_id = p_data.get("id")
                res_p = await db.execute(select(Player).filter(Player.id == p_id))
                player = res_p.scalars().first()
                if not player:
                    player = Player(
                        id=p_id,
                        name=p_data.get("name"),
                        first_name=p_data.get("first_name"),
                        last_name=p_data.get("last_name"),
                        image_url=p_data.get("image_url"),
                        team_id=team_a.id
                    )
                    db.add(player)
                else:
                    player.team_id = team_a.id
                    player.image_url = p_data.get("image_url")
        else:
            await sync_team_players(team_a_info["id"], team_a.id, game, db)
   
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
            
        if team_b_info.get("players"):
            for p_data in team_b_info.get("players", []):
                p_id = p_data.get("id")
                res_p = await db.execute(select(Player).filter(Player.id == p_id))
                player = res_p.scalars().first()
                if not player:
                    player = Player(
                        id=p_id,
                        name=p_data.get("name"),
                        first_name=p_data.get("first_name"),
                        last_name=p_data.get("last_name"),
                        image_url=p_data.get("image_url"),
                        team_id=team_b.id
                    )
                    db.add(player)
                else:
                    player.team_id = team_b.id
                    player.image_url = p_data.get("image_url")
        else:
            await sync_team_players(team_b_info["id"], team_b.id, game, db)
      
        begin_at = None
        if data.get("begin_at"):
            begin_at = datetime.fromisoformat(data["begin_at"].replace('Z', '+00:00'))

        score_a = 0
        score_b = 0
        for result in data.get("results", []):
            if result["team_id"] == team_a_info["id"]: score_a = result["score"]
            if result["team_id"] == team_b_info["id"]: score_b = result["score"]

        stream_url = None
        streams = data.get("streams_list", [])
        if streams:
            main_stream = next((s for s in streams if s.get("main")), None)
            if main_stream and main_stream.get("raw_url"):
                stream_url = main_stream["raw_url"]
            elif len(streams) > 0 and streams[0].get("raw_url"):
                stream_url = streams[0]["raw_url"]

        status = data["status"]
        pandascore_id = data["id"]
        number_of_games = data.get("number_of_games", 3)

        if status in ["finished", "canceled"] and score_a == 0 and score_b == 0:
            result_match = await db.execute(select(Match).filter(Match.pandascore_id == pandascore_id))
            match_to_delete = result_match.scalars().first()
            if match_to_delete:
                await db.delete(match_to_delete)
            continue 

        result_match = await db.execute(select(Match).filter(Match.pandascore_id == pandascore_id))
        match = result_match.scalars().first()
        
        if not match:
            match = Match(
                pandascore_id=pandascore_id,
                game=game.upper(),
                status=status,
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                team_a_score=score_a,
                team_b_score=score_b,
                begin_at=begin_at,
                league_id=league_id,
                stream_url=stream_url,
                number_of_games=number_of_games 
            )
            db.add(match)
            await db.flush()
        else:
            match.status = status
            match.team_a_score = score_a
            match.team_b_score = score_b
            match.begin_at = begin_at
            match.league_id = league_id 
            match.stream_url = stream_url
            match.number_of_games = number_of_games
            await db.flush()

        raw_games = data.get("games", [])
        for g_data in raw_games:
            game_id = g_data.get("id")
            winner_id = None
            if g_data.get("winner") and g_data.get("winner").get("id"):
                winner_id = g_data.get("winner").get("id")
                
            stmt_game = select(GameMap).filter(GameMap.id == game_id)
            res_game = await db.execute(stmt_game)
            db_game = res_game.scalars().first()
            
            if db_game:
                db_game.status = g_data.get("status")
                db_game.winner_id = winner_id
            else:
                new_game = GameMap(
                    id=game_id,
                    match_id=match.id,
                    position=g_data.get("position"),
                    status=g_data.get("status"),
                    winner_id=winner_id
                )
                db.add(new_game)
            
async def get_past_matches(game: str = "csgo", limit: int = 5):
    logger.info(f"Buscando os últimos {limit} resultados de {game.upper()}...")
    params = {"sort": "-begin_at", "per_page": limit}
    data = await request_pandascore(f"/{game}/matches/past", params=params)
    return data if data else []
            
async def get_running_matches(game: str = "csgo", limit: int = 10):
    logger.info(f"Buscando partidas AO VIVO de {game.upper()}...")
    params = {"sort": "begin_at", "per_page": limit}
    data = await request_pandascore(f"/{game}/matches/running", params=params)
    if data:
        logger.info(f" Encontradas {len(data)} partidas AO VIVO na API.")
        return data
    return []

async def get_match_by_id(match_id: int):
    return await request_pandascore(f"/matches/{match_id}")