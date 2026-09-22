from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.models.user import User
from app.models.team import Team
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import (
    get_password_hash, verify_password, create_access_token, decode_access_token,
)
from app.core.rate_limit import enforce_limit, ACCOUNT_LIMIT, USER_LIMIT

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# Same cost for an unknown account, to reduce timing-based account discovery.
DUMMY_HASH = get_password_hash("unused-dummy-password-for-timing")


class ProfileUpdate(BaseModel):
    favorite_team_id: int = Field(gt=0)


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    error = HTTPException(401, "Credenciais inválidas ou token expirado",
                          headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        raise error
    await enforce_limit(USER_LIMIT, "user", user_id)
    user = await db.get(User, user_id)
    if user is None:
        raise error
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.email == user_in.email) | (User.username == user_in.username))
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(400, "Nome de usuário ou email indisponível.")
    new_user = User(
        username=user_in.username, email=user_in.email,
        hashed_password=await run_in_threadpool(get_password_hash, user_in.password),
        avatar_url=f"https://ui-avatars.com/api/?name={quote(user_in.username, safe='')}&background=random",
    )
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Nome de usuário ou email indisponível.")
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    if len(form_data.username) > 254 or len(form_data.password) > 1024:
        raise HTTPException(401, "Email/Usuário ou senha incorretos",
                            headers={"WWW-Authenticate": "Bearer"})
    stmt = select(User).where((User.username == form_data.username) | (User.email == form_data.username))
    user = (await db.execute(stmt)).scalars().first()
    # Username and email aliases of an existing user share the same budget.
    identity = user.id if user else form_data.username.casefold()
    await enforce_limit(ACCOUNT_LIMIT, "login-account", identity)
    stored_hash = user.hashed_password if user and user.hashed_password else DUMMY_HASH
    valid = await run_in_threadpool(verify_password, form_data.password, stored_hash)
    if not user or not user.hashed_password or not valid:
        raise HTTPException(401, "Email/Usuário ou senha incorretos",
                            headers={"WWW-Authenticate": "Bearer"})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return {"access_token": create_access_token({"sub": user.id}), "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return current_user


@router.put("/profile/team", response_model=UserResponse)
async def update_favorite_team(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if await db.get(Team, profile_data.favorite_team_id) is None:
        raise HTTPException(404, "Time não encontrado")
    current_user.favorite_team_id = profile_data.favorite_team_id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Não foi possível atualizar o time favorito")
    await db.refresh(current_user)
    return current_user
