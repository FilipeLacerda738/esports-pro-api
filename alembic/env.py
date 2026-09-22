import asyncio
import sys
import os
from logging.config import fileConfig
from dotenv import load_dotenv

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context


sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.core.config import settings
from app.db.connection import database_connection_options
from app.db.base import Base
import app.models.team
import app.models.match
from app.models.league import League
from app.models.player import Player
from app.models.map import GameMap
from app.models.user import User

config = context.config


database_url, connection_args = database_connection_options(settings)


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata

def run_migrations_offline() -> None:
    
    url = database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    
    connectable = create_async_engine(
        database_url, connect_args=connection_args, poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
  
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()