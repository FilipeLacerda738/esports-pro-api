from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
import hashlib
import secrets
from uuid import UUID
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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict) -> str:
    subject = str(UUID(data["sub"]))
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": subject, "iat": now, "nbf": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
    }, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM],
            issuer=settings.JWT_ISSUER, audience=settings.JWT_AUDIENCE,
            options={"require": ["sub", "exp", "iat", "nbf", "iss", "aud"]},
        )
    except (jwt.MissingRequiredClaimError, jwt.InvalidAudienceError, jwt.InvalidIssuerError):
        # Accept sessions issued by the previous backend while they remain valid.
        # Signature and expiration still use the unchanged server secret.
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    try:
        return str(UUID(payload["sub"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise jwt.InvalidTokenError("Invalid subject") from exc

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pre_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    try:
        return pwd_context.verify(pre_hash, hashed_password)
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    pre_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(pre_hash)
