import httpx
from fastapi import APIRouter, HTTPException
from app.core.config import settings

router = APIRouter()

@router.get("/pandascore-raw-match/{match_id}")
async def test_get_raw_match(match_id: int):
    url = f"https://api.pandascore.co/matches/{match_id}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.PANDASCORE_API_KEY}"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, 
                detail=f"Erro direto da API PandaScore: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro de conexão com a PandaScore: {str(e)}"
            )