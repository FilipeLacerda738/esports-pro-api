from pydantic import BaseModel, ConfigDict
from typing import Optional 
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

  