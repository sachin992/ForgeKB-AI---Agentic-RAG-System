from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import db_url


class Base(DeclarativeBase):
    pass


engine = create_engine(db_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema_updates() -> None:
    insp = inspect(engine)

    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "role" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))

    if insp.has_table("document_registry"):
        cols = {c["name"] for c in insp.get_columns("document_registry")}
        with engine.begin() as conn:
            if "display_name" not in cols:
                conn.execute(text("ALTER TABLE document_registry ADD COLUMN display_name VARCHAR(255) NOT NULL DEFAULT ''"))
            if "owner_user_id" not in cols:
                conn.execute(text("ALTER TABLE document_registry ADD COLUMN owner_user_id INT NULL"))
                conn.execute(text("CREATE INDEX ix_document_registry_owner_user_id ON document_registry (owner_user_id)"))
            if "visibility" not in cols:
                conn.execute(text("ALTER TABLE document_registry ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private'"))
            if "metadata_json" not in cols:
                conn.execute(text("ALTER TABLE document_registry ADD COLUMN metadata_json TEXT NOT NULL"))
