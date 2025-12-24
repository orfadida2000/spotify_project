import keyword

from .constants import (
    _ALPHANUMERIC_GLOB,
    _BASE64_URL_SAFE_GLOB,
    _ISO_FULL_DATE_GLOB,
    _ISO_YEAR_GLOB,
    _ISO_YEAR_MONTH_GLOB,
)


def CHECK_ISO_YEAR_GLOB(col: str) -> str:  # noqa: N802
    return f"length({col}) = 4 AND {col} GLOB '{_ISO_YEAR_GLOB}'"


def CHECK_ISO_YEAR_MONTH_GLOB(col: str) -> str:  # noqa: N802
    return f"length({col}) = 7 AND {col} GLOB '{_ISO_YEAR_MONTH_GLOB}'"


def CHECK_ISO_FULL_DATE_GLOB(col: str) -> str:  # noqa: N802
    return f"length({col}) = 10 AND {col} GLOB '{_ISO_FULL_DATE_GLOB}'"


def CHECK_ALPHANUMERIC_GLOB(col: str) -> str:  # noqa: N802
    return f"{col} GLOB '{_ALPHANUMERIC_GLOB}*'"


def CHECK_BASE64_URL_SAFE_GLOB(col: str) -> str:  # noqa: N802
    return f"{col} GLOB '{_BASE64_URL_SAFE_GLOB}*'"


def is_valid_identifier(name: object) -> int:
    """
    Check if a string is a valid Python identifier.
    Returns an integer code indicating the result.

    Arguments:
        name: The string to check.

    Returns: (int)
        0 if valid identifier,
        1 if not a string,
        2 if empty string,
        3 if not a valid identifier,
        4 if a Python keyword.
    """
    if not isinstance(name, str):
        return 1
    if not name:
        return 2
    if not name.isidentifier():
        return 3
    if keyword.iskeyword(name):
        return 4
    return 0
