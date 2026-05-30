from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Match(Base):
  __tablename__ = "matches"

  id = Column(Integer, primary_key=True, index=True)

  pandascore_id = Column(Integer, unique=True, index=True, nullable=False)

  game = Column(String(50), nullable=False)
  status = Column(String(50), nullable=False)

  team_a_id = Column(Integer, ForeignKey("teams.id", ondelete='CASCADE'), nullable=True)
  team_b_id = Column(Integer, ForeignKey("teams.id", ondelete='CASCADE'), nullable=True)

  team_a_score = Column(Integer, default=0)
  team_b_score = Column(Integer, default=0)

  begin_at = Column(DateTime(timezone=True), nullable=True)
  
  stream_url = Column(String(255), nullable=True)
  number_of_games = Column(Integer, server_default="3", nullable=True)
  created_at = Column(DateTime(timezone=True), server_default=func.now())

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  team_a = relationship("Team", foreign_keys=[team_a_id], lazy="selectin")
  team_b = relationship("Team", foreign_keys=[team_b_id], lazy="selectin")
  league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True)
  league = relationship("League", back_populates="matches")