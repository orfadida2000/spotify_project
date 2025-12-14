import sqlite3
from pathlib import Path

from sp2genius.utils import err_msg
from sp2genius.utils.path import get_absolute_path

from . import DB_PATH
from .schema import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_META_TABLE,
    SQL_CREATE_STATEMENTS,
    SQL_PRAGMA_STATEMENT,
    VALID_SCHEMA_ID,
)


def initialize_db(db_path: str | Path | None = None) -> None:
    if db_path is None:
        db_path = DB_PATH
    db_path = get_absolute_path(db_path)
    if db_path is None:
        raise ValueError(err_msg("The provided db_path is empty or invalid."))

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(SQL_PRAGMA_STATEMENT)

        # Ensure schema_meta exists
        conn.execute(SCHEMA_META_TABLE)

        # Check current DB version
        row = conn.execute(
            "SELECT version FROM schema_meta WHERE id = :id",
            {"id": VALID_SCHEMA_ID},
        ).fetchone()

        if row is None:
            # Brand-new DB: create all tables and set version
            conn.executescript(SQL_CREATE_STATEMENTS)
            conn.execute(
                "INSERT INTO schema_meta (id, version) VALUES (:id, :version)",
                {"id": VALID_SCHEMA_ID, "version": CURRENT_SCHEMA_VERSION},
            )
        else:
            db_version = row[0]
            if db_version < CURRENT_SCHEMA_VERSION:
                raise NotImplementedError(
                    err_msg(
                        f"Database schema version {db_version} is outdated. "
                        f"Current version is {CURRENT_SCHEMA_VERSION}. "
                        "Automatic migrations are not yet implemented."
                    )
                )
            elif db_version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    err_msg(
                        f"Database schema version {db_version} is newer than the current "
                        f"supported version {CURRENT_SCHEMA_VERSION}. "
                        "Please update the application."
                    )
                )

        conn.commit()
    finally:
        conn.close()
