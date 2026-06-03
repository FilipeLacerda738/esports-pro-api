# app/models/player.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True) 
    name = Column(String, index=True) 
    first_name = Column(String, nullable=True) 
    last_name = Column(String, nullable=True) 
    image_url = Column(String, nullable=True) 
    
    
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"))
    
    
    team = relationship("Team", back_populates="players")