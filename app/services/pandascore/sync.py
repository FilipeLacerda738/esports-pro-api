from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.logger import logger
from app.models.team import Team
from app.models.match import Match
from app.models.league import League 
from app.models.map import GameMap
from app.models.player import Player
from app.services.pandascore.client import get_team_roster

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

async def _get_or_create_league(league_info: dict, db: AsyncSession) -> int:
    if not league_info:
        return None
        
    league_ps_id = league_info.get("id")
    result_league = await db.execute(select(League).filter(League.pandascore_id == league_ps_id))
    league = result_league.scalars().first()
    
    if not league:
        result_old_league = await db.execute(select(League).filter(League.id == league_ps_id))
        league = result_old_league.scalars().first()
        
        if league:
            league.pandascore_id = league_ps_id 
        else:
            league = League(
                pandascore_id=league_ps_id,
                name=league_info.get("name", "Desconhecido"),
                image_url=league_info.get("image_url"),
                dark_mode_image_url=league_info.get("dark_mode_image_url") # NOVO
            )
            db.add(league)
    else:
        if league_info.get("image_url"):
            league.image_url = league_info.get("image_url")
        if league_info.get("dark_mode_image_url"):
            league.dark_mode_image_url = league_info.get("dark_mode_image_url") # NOVO
            
    await db.flush() 
    return league.id

async def _get_or_create_team(team_info: dict, game: str, db: AsyncSession) -> Team:
    team_ps_id = team_info["id"]
    result = await db.execute(select(Team).filter(Team.pandascore_id == team_ps_id))
    team = result.scalars().first()
    
    if not team:
        result_old = await db.execute(select(Team).filter(Team.name == team_info["name"], Team.game == game.upper()))
        team = result_old.scalars().first()
        
        if team:
            team.pandascore_id = team_ps_id 
        else:
            team = Team(
                pandascore_id=team_ps_id,
                name=team_info["name"], 
                acronym=team_info.get("acronym"), 
                image_url=team_info.get("image_url"), 
                dark_mode_image_url=team_info.get("dark_mode_image_url"), 
                location=team_info.get("location"), 
                game=game.upper()
            )
            db.add(team)
    else:
        if team_info.get("image_url"): team.image_url = team_info.get("image_url")
        if team_info.get("dark_mode_image_url"): team.dark_mode_image_url = team_info.get("dark_mode_image_url")
        if team_info.get("location"): team.location = team_info.get("location")

    await db.flush()
        
    if team_info.get("players"):
        for p_data in team_info.get("players", []):
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
                    team_id=team.id
                )
                db.add(player)
            else:
                player.team_id = team.id
                player.image_url = p_data.get("image_url")
    else:
        await sync_team_players(team_ps_id, team.id, game, db)
        
    return team

async def sync_matches_to_db(matches_data: list, db: AsyncSession, game: str):
    for data in matches_data:
        tournament_info = data.get("tournament") or {}
        tier = tournament_info.get("tier")
        prizepool = tournament_info.get("prizepool") 

        if str(tier).lower() not in ["s", "a", "b"]:
            continue

        opponents = data.get("opponents", [])
        if len(opponents) != 2:
            continue

        league_internal_id = await _get_or_create_league(data.get("league"), db)
        team_a = await _get_or_create_team(opponents[0]["opponent"], game, db)
        team_b = await _get_or_create_team(opponents[1]["opponent"], game, db)
      
        begin_at = None
        if data.get("begin_at"):
            begin_at = datetime.fromisoformat(data["begin_at"].replace('Z', '+00:00'))

        score_a = 0
        score_b = 0
        for result in data.get("results", []):
            if result["team_id"] == opponents[0]["opponent"]["id"]: score_a = result["score"]
            if result["team_id"] == opponents[1]["opponent"]["id"]: score_b = result["score"]

        stream_url = None
        streams_list = data.get("streams_list", []) 
        if streams_list:
            main_stream = next((s for s in streams_list if s.get("main")), None)
            if main_stream and main_stream.get("raw_url"):
                stream_url = main_stream["raw_url"]
            elif len(streams_list) > 0 and streams_list[0].get("raw_url"):
                stream_url = streams_list[0]["raw_url"]

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
                league_id=league_internal_id,
                stream_url=stream_url,
                streams=streams_list, 
                tier=tier,
                prizepool=str(prizepool) if prizepool else None, 
                number_of_games=number_of_games 
            )
            db.add(match)
            await db.flush()
        else:
            match.status = status
            match.team_a_score = score_a
            match.team_b_score = score_b
            match.begin_at = begin_at
            match.league_id = league_internal_id 
            match.stream_url = stream_url
            match.streams = streams_list 
            match.tier = tier 
            match.prizepool = str(prizepool) if prizepool else None
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