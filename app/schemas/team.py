from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class TeamBase(BaseModel):
    name: str
    acronym: Optional[str] = None
    image_url: Optional[str] = None
    game: str

class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PlayerSchema(BaseModel):
    id: int
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TeamDetailSchema(BaseModel):
    id: int
    name: str
    acronym: Optional[str] = None
    image_url: Optional[str] = None
    players: List[PlayerSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)