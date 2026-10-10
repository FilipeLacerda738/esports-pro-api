import asyncio
import sys
import ipaddress
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from app.core.config import settings
from app.db.base import Base
from app.models.league import League
from app.models.team import Team
from app.models.match import Match
from app.models.player import Player
from app.models.map import GameMap

async def reset_database():
    if settings.ENVIRONMENT != "development" or not is_local_database(settings.DATABASE_URL):
        print(f"ALERTA CRÍTICO: Tentativa de reset em ambiente '{settings.ENVIRONMENT}'.")
        print("Operação bloqueada. Esse script só tem permissão para rodar no ambiente local de desenvolvimento.")
        sys.exit(1)

    print("Isso vai apagar TODOS os dados do banco")
    confirmacao = input("Tem certeza que deseja continuar? 'SIM': ")
    
    if confirmacao != "SIM":
        print("Operação abortada.")
        sys.exit(0)

    print("Iniciando o reset do banco de dados...")
    from app.db.session import engine
    
    async with engine.begin() as conn:
        print("Apagando tabelas antigas...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Criando novas tabelas...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Banco de dados recriado")


def is_local_database(raw_url):
    try:
        url = make_url(raw_url)
        if url.query or not url.host:
            return False
        if url.host == "localhost":
            return True
        return ipaddress.ip_address(url.host).is_loopback
    except (ValueError, TypeError, ArgumentError):
        return False

if __name__ == "__main__":
    asyncio.run(reset_database())
