from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
import hashlib
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == settings.API_ACCESS_KEY:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso Negado: Chave de API inválida ou ausente.",
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pre_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(pre_hash, hashed_password)

def get_password_hash(password: str) -> str:
    pre_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(pre_hash)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)