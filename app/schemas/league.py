from pydantic import BaseModel, ConfigDict
from typing import Optional

class LeagueResponse(BaseModel):
    id: int
    pandascore_id: Optional[int] = None
    name: str
    image_url: Optional[str] = None
    dark_mode_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)