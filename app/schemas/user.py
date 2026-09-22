# app/schemas/user.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(...,
                          min_length=6,
                          max_length=72,
                          description="A senha deve ter no mínimo 6 caracteres")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    avatar_url: Optional[str] = None
    favorite_team_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
