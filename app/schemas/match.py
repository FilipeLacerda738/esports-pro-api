from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


from app.schemas.team import TeamDetailSchema 

class TeamBasicInfo(BaseModel):
    id: int
    name: str
    acronym: Optional[str] = None
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LeagueResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MatchResponse(BaseModel):


    id: int
    game: str
    status: str
    number_of_games: Optional[int] = 3 
    begin_at: Optional[datetime] = None
    team_a_score: int
    team_b_score: int
    stream_url: Optional[str] = None

    team_a: Optional[TeamBasicInfo] = None
    team_b: Optional[TeamBasicInfo] = None
    league: Optional[LeagueResponse] = None

    model_config = ConfigDict(from_attributes=True)



class GameMapSchema(BaseModel):
    id: int
    position: int
    status: str
    map_name: Optional[str] = None
    winner_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class MatchDetailResponse(BaseModel):
  
    id: int
    game: str
    status: str
    number_of_games: Optional[int] = 3 
    begin_at: Optional[datetime] = None
    team_a_score: int
    team_b_score: int
    stream_url: Optional[str] = None
    league: Optional[LeagueResponse] = None
    
  
    team_a: Optional[TeamDetailSchema] = None
    team_b: Optional[TeamDetailSchema] = None
    
    games: List[GameMapSchema] = []

    model_config = ConfigDict(from_attributes=True)

class PaginatedMatchResponse(BaseModel):
    total: int
    page: int
    size: int
    has_more: bool
    items: List[MatchResponse]

    model_config = ConfigDict(from_attributes=True)