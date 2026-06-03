from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func 
from sqlalchemy.orm import relationship
from app.db.base import Base

class Team(Base):
  __tablename__ = "teams"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(100), nullable=False, index=True)
  acronym = Column(String(10), nullable=True)
  image_url = Column(String, nullable=True)
  game = Column(String(50), nullable=False)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())
  players = relationship("Player", back_populates="team")