from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


# Base SQLAlchemy, moteur et fabrique de sessions partagés avec les migrations.
class Base(DeclarativeBase):
    pass


def build_engine():
    url = get_settings().database_url
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Fournit une session par requête et la ferme automatiquement à la fin.
def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db
