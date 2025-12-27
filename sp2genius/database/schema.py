from typing import Final

from .core.constants import FOREIGN_KEYS
from .core.typing import CreateStatement
from .genius.tables import TABLES as GENIUS_TABLES
from .spotify.tables import TABLES as SPOTIFY_TABLES

SQL_PRAGMA_STATEMENT: Final[str] = f"PRAGMA foreign_keys = {'ON' if FOREIGN_KEYS else 'OFF'};"

CURRENT_SCHEMA_VERSION: Final[int] = 1

SCHEMA_META_TABLE_NAME: Final[str] = "schema_meta"
SCHEMA_META_ID_COLUMN: Final[str] = "id"
SCHEMA_META_VERSION_COLUMN: Final[str] = "version"
VALID_SCHEMA_ID: Final[int] = 1
SCHEMA_META_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_META_TABLE_NAME} (
    {SCHEMA_META_ID_COLUMN}      INTEGER PRIMARY KEY CHECK ({SCHEMA_META_ID_COLUMN} = {VALID_SCHEMA_ID}),
    {SCHEMA_META_VERSION_COLUMN} INTEGER NOT NULL CHECK ({SCHEMA_META_VERSION_COLUMN} >= 0)
) STRICT;
"""


CREATE_STATEMENT_LST: list[CreateStatement] = GENIUS_TABLES + SPOTIFY_TABLES
for statement in CREATE_STATEMENT_LST:
    statement = statement.strip()
    if not statement.endswith(";"):
        statement += ";"
    CREATE_STATEMENT_LST.append(statement)

SQL_CREATE_STATEMENTS: Final[str] = "\n".join(CREATE_STATEMENT_LST)
