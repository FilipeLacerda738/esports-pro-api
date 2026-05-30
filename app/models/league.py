from sqlalchemy import Column, Integer, String
from app.db.base import Base  
from sqlalchemy.orm import relationship

class League(Base):
    __tablename__ = "leagues"

    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=True)  

    matches = relationship("Match", back_populates="league")