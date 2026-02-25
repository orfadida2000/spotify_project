import re
import sqlite3
from typing import Final

# General Database Constants and Utilities
CONCAT: Final[str] = "||"  # SQLite string concatenation operator
FOREIGN_KEYS: Final[bool] = True
STRICT_TABLES: Final[bool] = True
SQLITE_MAX_BIND_PARAMS: Final[int] = 999

# Date and String Pattern Globs for CHECK Constraints
_YEAR_GLOB: Final[str] = r"[0-9][0-9][0-9][0-9]"
_MONTH_GLOB: Final[str] = r"[0-9][0-9]"
_DAY_GLOB: Final[str] = r"[0-9][0-9]"
_ISO_YEAR_GLOB: Final[str] = f"{_YEAR_GLOB}"
_ISO_YEAR_MONTH_GLOB: Final[str] = f"{_YEAR_GLOB}-{_MONTH_GLOB}"
_ISO_FULL_DATE_GLOB: Final[str] = f"{_YEAR_GLOB}-{_MONTH_GLOB}-{_DAY_GLOB}"
_ALPHANUMERIC_GLOB: Final[str] = r"[A-Za-z0-9]"
_BASE64_URL_SAFE_GLOB: Final[str] = r"[A-Za-z0-9_-]"


def _get_sql_keywords() -> frozenset[str]:
    """
    Helper for fetching SQLite keywords.
    """
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("SELECT keyword FROM pragma_keyword_list();")
    keywords = {row[0].upper() for row in cur.fetchall()}
    conn.close()
    return frozenset(keywords)


SQL_KEYWORDS: Final[frozenset[str]] = _get_sql_keywords()
SQL_IDENTIFIER_ESCAPE_CHARS_OPEN_CLOSE_MAP: Final[dict[str, str]] = {
    '"': '"',
    "`": "`",
    "[": "]",
    "'": "'",
}
SQL_IDENTIFIER_FORBIDDEN_PREFIXES: Final[tuple[str, ...]] = (
    "sqlite_",
    "pg_",
    "sys_",
    "ora_",
    "mysql_",
    "ms_",
    "ibm_",
)
SQL_IDENTIFIER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SQL_IDENTIFIER_MAX_LENGTH: Final[int] = 63
