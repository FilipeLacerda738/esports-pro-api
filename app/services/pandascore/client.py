import httpx
from app.core.logger import logger
from app.core.config import settings

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

async def get_upcoming_matches(game: str = "csgo", limit: int = 5):
    logger.info(f"Buscando as próximas {limit} partidas de {game.upper()}...")
    params = {"sort": "begin_at", "per_page": limit}
    data = await request_pandascore(f"/{game}/matches/upcoming", params=params)
    if data:
        logger.info(f"Encontradas {len(data)} partidas na API.")
        return data
    return []

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