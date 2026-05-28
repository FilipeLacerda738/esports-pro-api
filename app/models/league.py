from sqlalchemy import Column, Integer, String
from app.db.base import Base  

class League(Base):
    __tablename__ = "leagues"

    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=True)  