from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.resolved_database_url.startswith("sqlite") else {}

engine = create_engine(settings.resolved_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
async_engine = create_async_engine(settings.resolved_effective_async_database_url)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def init_sqlite_schema_for_dev() -> None:
    """Create local SQLite tables when running the app without Alembic.

    PostgreSQL deployments should continue to use Alembic migrations. This
    helper exists for local Swagger/frontend smoke tests where the configured
    SQLite file may not exist yet.
    """
    if not settings.resolved_database_url.startswith("sqlite"):
        return
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
