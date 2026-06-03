# app/models/game_map.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class GameMap(Base):
    __tablename__ = "game_maps"

    id = Column(Integer, primary_key=True, index=True) 
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"))
    
    position = Column(Integer) 
    status = Column(String) 
    map_name = Column(String, nullable=True) 
    winner_id = Column(Integer, nullable=True) 
    
    
    match = relationship("Match", back_populates="games")