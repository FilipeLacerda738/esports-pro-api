import gc
from app.core.synchronization import serialized_sync
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.match import Match
from app.core.logger import logger
from app.services.pandascore import (
    get_upcoming_matches, 
    get_past_matches, 
    get_running_matches, 
    sync_matches_to_db,
    get_match_by_id
)

@serialized_sync
async def update_live_matches_task():
    logger.info("Buscando atualizações AO VIVO...")
    jogos = ["valorant", "csgo"] 
    try:
        async with SessionLocal() as db: 
            for jogo in jogos:
                try:
                    running_data = await get_running_matches(game=jogo, limit=15)
                    if running_data:
                        await sync_matches_to_db(matches_data=running_data, db=db, game=jogo)
                    stmt = select(Match).filter(Match.status == "running", Match.game == jogo.upper())
                    result = await db.execute(stmt)
                    running_db = result.scalars().all()

                    if running_db:
                        sniper_data = []
                        for m in running_db:
                            fresh = await get_match_by_id(m.pandascore_id)
                            if fresh:
                                sniper_data.append(fresh)
                        
                        if sniper_data:
                            await sync_matches_to_db(matches_data=sniper_data, db=db, game=jogo)
                    
                    await db.commit() 
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Erro crítico no Live Task ({jogo}): {e}", exc_info=True)
    finally:
        gc.collect()

@serialized_sync
async def update_static_matches_task():
    logger.info("Sincronizando calendário e resultados...")
    jogos = ["valorant", "csgo"] 
    try:
        async with SessionLocal() as db: 
            for jogo in jogos:
                try:
                    upcoming_data = await get_upcoming_matches(game=jogo, limit=30)
                    if upcoming_data:
                        await sync_matches_to_db(matches_data=upcoming_data, db=db, game=jogo)
                        
                    past_data = await get_past_matches(game=jogo, limit=30)
                    if past_data:
                        await sync_matches_to_db(matches_data=past_data, db=db, game=jogo)
                    
                    await db.commit() 
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Erro crítico no Static Task ({jogo}): {e}", exc_info=True)
    finally:
        gc.collect()

@serialized_sync
async def cleanup_old_matches_task():
    logger.info("Iniciando limpeza profunda de histórico...")
    try:
        data_limite = datetime.now(timezone.utc) - timedelta(days=10)
        
        async with SessionLocal() as db:
            stmt = (
                delete(Match)
                .where(Match.status == "finished")
                .where(Match.begin_at < data_limite)
            )
            resultado = await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Limpeza de banco concluída: {resultado.rowcount} partidas antigas apagadas.")
            
    except Exception as e:
        logger.error(f"Erro crítico na limpeza profunda: {e}")
    finally:
        gc.collect()

@serialized_sync
async def resolve_stuck_matches_task():
    logger.info("Iniciando inspeção e resgate de partidas travadas...")
    try:
        now = datetime.now(timezone.utc)
        limite_tempo = now - timedelta(hours=3)
        
        async with SessionLocal() as db:
            stmt_stuck = select(Match).where(
                Match.begin_at < limite_tempo,
                Match.status.in_(["not_started", "running"])
            )
            result = await db.execute(stmt_stuck)
            stuck_matches = result.scalars().all()

            if stuck_matches:
                logger.info(f"Encontradas {len(stuck_matches)} partidas travadas. Fazendo a ÚLTIMA VERIFICAÇÃO na API...")
                sniper_data = []
                
                for match in stuck_matches:
                    fresh_data = await get_match_by_id(match.pandascore_id)
                    if isinstance(fresh_data, dict) and fresh_data.get("id") == match.pandascore_id:
                        sniper_data.append(fresh_data)
                
                if sniper_data:
                    csgo_data = [d for d in sniper_data if d.get("videogame", {}).get("slug") == "cs-go"]
                    valorant_data = [d for d in sniper_data if d.get("videogame", {}).get("slug") == "valorant"]
                    
                    if csgo_data: await sync_matches_to_db(csgo_data, db, "csgo")
                    if valorant_data: await sync_matches_to_db(valorant_data, db, "valorant")

            await db.commit()
                
    except Exception as e:
        logger.error(f"Erro na rotina de inspeção: {e}")
    finally:
        gc.collect()