"""Database engine and session.

create_all, not Alembic: there is no production data to migrate in 48 hours.
After any model change, run `docker compose down -v` to drop the volume,
then `docker compose up` to recreate the tables.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # survives Postgres restarting under us
)


#: Any constant, as long as every process uses the same one.
_SCHEMA_LOCK_ID = 7_283_461_905


def create_db_and_tables() -> None:
    # Importing the models registers them on SQLModel.metadata before create_all.
    from app import models  # noqa: F401

    _refuse_outdated_schema()
    # Two processes can start at once (the server and `python -m app.check_llm`,
    # or several workers). On PostgreSQL, CREATE TYPE for an enum is not safe to
    # race and fails with "duplicate key ... pg_type_typname_nsp_index". An
    # advisory lock makes the second process wait, then see the tables exist.
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": _SCHEMA_LOCK_ID})
        SQLModel.metadata.create_all(connection)


class OutdatedSchemaError(RuntimeError):
    """The database was created by an older version of the models."""


def _refuse_outdated_schema() -> None:
    """create_all adds missing tables but never changes columns. A database
    made while accounts existed still has conversations.owner_id and
    share_links.created_by (NOT NULL), and new share links would fail later
    with a confusing SQL error. Fail now, with the fix."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    old_columns = {
        "conversations": "owner_id",
        "share_links": "created_by",
    }
    for table, column in old_columns.items():
        if table in tables and column in {c["name"] for c in inspector.get_columns(table)}:
            raise OutdatedSchemaError(
                "The database was created when the app still had accounts. Reset it with "
                "`docker compose down -v` and then `docker compose up --build`. "
                "This deletes stored chats and the AI cache."
            )


def get_session() -> Iterator[Session]:
    """FastAPI dependency. One session per request, committed by the caller."""
    with Session(engine) as session:
        yield session
