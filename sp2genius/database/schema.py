from typing import Final

from .core import FOREIGN_KEYS
from .genius.tables import TABLES as GENIUS_TABLES
from .spotify.tables import TABLES as SPOTIFY_TABLES

SQL_PRAGMA_STATEMENT: Final[str] = f"PRAGMA foreign_keys = {'ON' if FOREIGN_KEYS else 'OFF'};"

CURRENT_SCHEMA_VERSION: Final[int] = 1

VALID_SCHEMA_ID: Final[int] = 1
SCHEMA_META_TABLE: Final[str] = f"""
CREATE TABLE IF NOT EXISTS schema_meta (
    id      INTEGER PRIMARY KEY CHECK (id = {VALID_SCHEMA_ID}),
    version INTEGER NOT NULL CHECK (version >= 0)
);
"""

FULL_TABLES: Final[list[str]] = GENIUS_TABLES + SPOTIFY_TABLES
SQL_CREATE_STATEMENTS: Final[str] = ("\n".join(FULL_TABLES)).strip()
if not SQL_CREATE_STATEMENTS.endswith(";"):
    raise RuntimeError("SQL_CREATE_STATEMENTS is malformed: does not end with a semicolon.")
