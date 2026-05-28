from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TeamBasicInfo(BaseModel):
  id: int
  name: str
  acronym: Optional[str] = None
  image_url: Optional[str] = None

  class config: 
    from_attributes = True

class LeagueResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class MatchResponse(BaseModel):
  id: int
  game: str
  status: str
  begin_at: Optional[datetime] = None
  team_a_score: int
  team_b_score: int

  team_a: Optional[TeamBasicInfo] = None
  team_b: Optional[TeamBasicInfo] = None

  league: Optional[LeagueResponse] = None

  class Config:
    from_attributes = True




