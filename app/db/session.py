from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.connection import database_options

url_banco, connection_args = database_options(settings.DATABASE_URL)

engine = create_async_engine(
    url_banco, 
    echo=False, 
    future=True,
    connect_args=connection_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with SessionLocal() as session:
        yield session
