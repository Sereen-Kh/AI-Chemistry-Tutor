from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import BACKEND_DIR, settings

_is_sqlite = settings.resolved_database_url.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(settings.resolved_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_async_connect_args = {"timeout": 30} if _is_sqlite else {}
async_engine = create_async_engine(
    settings.resolved_effective_async_database_url,
    connect_args=_async_connect_args,
)

if _is_sqlite:
    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_sqlite_wal(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

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
    """Run Alembic for local SQLite development databases.

    This keeps local Swagger/frontend smoke tests on the same schema path as
    PostgreSQL deployments and avoids direct metadata table creation.
    """
    if not settings.resolved_database_url.startswith("sqlite"):
        return

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.resolved_database_url)
    command.upgrade(alembic_cfg, "head")
