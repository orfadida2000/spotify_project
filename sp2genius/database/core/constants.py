from typing import Final

from .typing import _UnsetType

# UNSET Singleton Instance
UNSET: Final[_UnsetType] = _UnsetType()

# General Database Constants and Utilities
CONCAT: Final[str] = "||"  # SQLite string concatenation operator
FOREIGN_KEYS: Final[bool] = True

# Date and String Pattern Globs for CHECK Constraints
_YEAR_GLOB: Final[str] = r"[0-9][0-9][0-9][0-9]"
_MONTH_GLOB: Final[str] = r"[0-9][0-9]"
_DAY_GLOB: Final[str] = r"[0-9][0-9]"
_ISO_YEAR_GLOB: Final[str] = f"{_YEAR_GLOB}"
_ISO_YEAR_MONTH_GLOB: Final[str] = f"{_YEAR_GLOB}-{_MONTH_GLOB}"
_ISO_FULL_DATE_GLOB: Final[str] = f"{_YEAR_GLOB}-{_MONTH_GLOB}-{_DAY_GLOB}"
_ALPHANUMERIC_GLOB: Final[str] = r"[A-Za-z0-9]"
_BASE64_URL_SAFE_GLOB: Final[str] = r"[A-Za-z0-9_-]"


# constants for internal use, used for semantic purposes
_CONCRETE_ENTITY_FLAG: Final[str] = "_CONCRETE_ENTITY"
_SCHEMA_META: Final[str] = "TABLE_META"
