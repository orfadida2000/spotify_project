import re

from .constants import (
    _ALPHANUMERIC_GLOB,
    _BASE64_URL_SAFE_GLOB,
    _ISO_FULL_DATE_GLOB,
    _ISO_YEAR_GLOB,
    _ISO_YEAR_MONTH_GLOB,
    SQL_IDENTIFIER_ESCAPE_CHARS_OPEN_CLOSE_MAP,
    SQL_IDENTIFIER_FORBIDDEN_PREFIXES,
    SQL_IDENTIFIER_MAX_LENGTH,
    SQL_KEYWORDS,
    SQLITE_MAX_BIND_PARAMS,
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


def get_effective_max_bind_params(max_bind_params: int) -> int:
    assert isinstance(max_bind_params, int) and max_bind_params > 0, (
        "max_bind_params must be a positive integer"
    )
    return min(max_bind_params, SQLITE_MAX_BIND_PARAMS)


def sanitize_sql_identifier(identifier: str, strict: bool = True) -> str:
    # First phase: basic normalization and validation (not dependent on strictness)
    if not isinstance(strict, bool):
        raise TypeError(f"strict must be bool, got: {type(strict)}")
    if not isinstance(identifier, str):
        raise TypeError(f"Identifier name must be str, got: {type(identifier)}")
    norm_name = identifier.strip().lower()
    if not norm_name:
        raise ValueError("Identifier name cannot be empty (after stripping)")
    while True:
        if len(norm_name) < 2:
            break
        open_char = norm_name[0]
        close_char = norm_name[-1]
        if open_char in SQL_IDENTIFIER_ESCAPE_CHARS_OPEN_CLOSE_MAP:
            expected_close_char = SQL_IDENTIFIER_ESCAPE_CHARS_OPEN_CLOSE_MAP[open_char]
            if close_char == expected_close_char:
                norm_name = norm_name[1:-1].strip()
                continue
        break
    if not norm_name:
        raise ValueError(
            "Identifier name cannot be empty (after peeling escape chars and stripping)"
        )

    norm_name = re.sub(r"\s+", "_", norm_name)

    if norm_name.upper() in SQL_KEYWORDS:
        raise ValueError(f"Identifier name cannot be SQL keyword: {norm_name!r}")

    # Second phase: strictness-dependent validation
    if norm_name[0].isdigit():
        if strict:
            raise ValueError(f"Identifier name cannot start with a digit: {norm_name!r}")
        else:
            norm_name = f"_{norm_name}"

    for prefix in SQL_IDENTIFIER_FORBIDDEN_PREFIXES:
        if norm_name.startswith(prefix):
            if strict:
                raise ValueError(
                    f"Identifier name cannot start with forbidden prefix {prefix!r}: {norm_name!r}"
                )
            else:
                norm_name = f"_{norm_name}"

    repl_norm_name = re.sub(r"[^a-zA-Z0-9_]", "*", norm_name)
    if "*" in norm_name:
        if strict:
            raise ValueError(
                "Identifier name contains invalid characters which were replaced with '*'\n"
                f"Original (post phase 1 normalization): {norm_name!r}\n"
                f"Invalid chars replaced version: {repl_norm_name!r}"
            )
        else:
            norm_name = repl_norm_name.strip("*")
            norm_name = re.sub(r"\*+", "_", norm_name)
            if not norm_name:
                raise ValueError("Identifier name became empty after replacing invalid characters")

    # Extra check against all underscore name (at this point we know it's non-empty)
    # This validates against ugly names like "_" or "____"
    assert norm_name, "Internal error: norm_name should be non-empty here"
    if all(c == "_" for c in norm_name):
        raise ValueError(
            f"Identifier name (post all normalizations) cannot consist solely of underscore characters: {norm_name!r}"
        )

    # Final length check
    if len(norm_name) > SQL_IDENTIFIER_MAX_LENGTH:
        raise ValueError(
            f"Identifier name exceeds maximum length of {SQL_IDENTIFIER_MAX_LENGTH} characters: {norm_name!r}"
        )

    return norm_name
