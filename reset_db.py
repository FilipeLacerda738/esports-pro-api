import asyncio
from app.db.session import engine
from app.db.base import Base
from app.models.league import League
from app.models.team import Team
from app.models.match import Match
from app.models.player import Player
from app.models.map import GameMap

async def reset_database():
    print(" Iniciando o reset do banco de dados...")
    
    async with engine.begin() as conn:
        print(" Apagando tabelas antigas (drop_all)...")
        
        await conn.run_sync(Base.metadata.drop_all)
        
        print(" Criando novas tabelas (create_all)...")
        await conn.run_sync(Base.metadata.create_all)
        
    print(" Banco de dados recriado com sucesso")

if __name__ == "__main__":
    asyncio.run(reset_database())