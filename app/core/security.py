import secrets
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key and secrets.compare_digest(api_key.encode(), settings.API_ACCESS_KEY.encode()):
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso Negado: Chave de API inválida ou ausente.",
    )

async def get_admin_key(api_key: str = Security(api_key_header)):
    if (settings.ADMIN_API_KEY and api_key
            and settings.ADMIN_API_KEY != settings.API_ACCESS_KEY
            and secrets.compare_digest(api_key.encode(), settings.ADMIN_API_KEY.encode())):
        return api_key
    raise HTTPException(status_code=403, detail="Administrative access required")
