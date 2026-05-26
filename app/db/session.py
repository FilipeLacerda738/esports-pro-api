from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


url_banco = settings.DATABASE_URL


if url_banco.startswith("postgresql://"):
    url_banco = url_banco.replace("postgresql://", "postgresql+asyncpg://", 1)
elif url_banco.startswith("postgres://"):
    url_banco = url_banco.replace("postgres://", "postgresql+asyncpg://", 1)


if "?sslmode=require" in url_banco:
    url_banco = url_banco.replace("?sslmode=require", "")


engine = create_async_engine(url_banco, echo=True, future=True)

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