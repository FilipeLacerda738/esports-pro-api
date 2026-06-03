import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AppVersionResponse(BaseModel):
    version: str
    download_url: str
    release_notes: str

@router.get("/app-version", response_model=AppVersionResponse)
async def get_latest_app_version():

    github_api_url = "https://api.github.com/repos/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(github_api_url)
            response.raise_for_status() 
            data = response.json()
            latest_version = data.get("tag_name", "").replace("v", "")
            release_notes = data.get("body", "Nova atualização disponível para download!")
            
        except Exception:
            latest_version = "1.0.0"
            release_notes = ""

    return {
        "version": latest_version,
        "download_url": "https://github.com/FilipeLacerda738/EsportsNewsAppAndroid/releases/latest",
        "release_notes": release_notes
    }