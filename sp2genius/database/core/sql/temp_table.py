import sqlite3
from collections.abc import Iterable, Sequence
from sqlite3 import _Parameters

from sp2genius.database.core.typing import TableColumn

from ..typing import SqlColType
from . import STRICT_TABLES


def init_temp_table(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    columns: Sequence[TableColumn],
    primary_keys: Sequence[str],
    rows: Iterable[_Parameters],
    wipe: bool = True,
) -> None:
    """
    Create a TEMP table (optionally STRICT), optionally wipe it, and insert rows.

    - primary_keys: Sequence of column names that form the PK (can be composite).
    - For TempColType.BOOLEAN, we add: CHECK (col IS NULL OR col IN (0, 1)) if the column is nullable,
      else CHECK (col IN (0, 1)).
    - Marking PK columns as UNIQUE is harmless (redundant/no-op logically).
    """
    if not columns or len(columns) == 0:
        raise ValueError("Temp table must have at least one column")

    max_col_name: int = -1
    col_by_name: set[str] = set()
    pk_set: set[str] = set()

    for col in columns:
        if len(col.name) > max_col_name:
            max_col_name = len(col.name)
        if col.name in col_by_name:
            raise ValueError(f"Duplicate column name: {col.name!r}")
        col_by_name.add(col.name)

    if not primary_keys or len(primary_keys) == 0:
        raise ValueError("primary_key must be non-empty")

    for pk_col in primary_keys:
        if not isinstance(pk_col, str):
            raise TypeError(f"primary_key column name must be str, got: {type(pk_col)}")
        if pk_col not in col_by_name:
            raise ValueError(f"primary_key refers to unknown column: {pk_col!r}")
        if pk_col in pk_set:
            raise ValueError(f"Duplicate primary_key column name: {pk_col!r}")
        pk_set.add(pk_col)

    col_defs: list[str] = []
    col_names: list[str] = []

    for col in columns:
        col_name = col.name
        col_def = f"{' ' * 4}{col_name}{' ' * (max_col_name - len(col_name))} {col.sql_type.declared_type}"

        if col_name not in pk_set:
            if not col.nullable:
                col_def += " NOT NULL"

        if col_name not in pk_set or len(pk_set) > 1:
            if col.unique:
                col_def += " UNIQUE"

        if col.sql_type is SqlColType.BOOLEAN:
            # With NOT NULL, this enforces {0,1}. With NULL allowed, NULL also passes.
            check_indent = f"\n{' ' * (4 + max_col_name + 1 + 4)}"
            if not col.nullable:
                col_def += f"{check_indent}CHECK ({col.name} IN (0, 1))"
            else:
                col_def += f"{check_indent}CHECK ({col.name} IS NULL OR {col.name} IN (0, 1))"

        col_defs.append(col_def)
        col_names.append(col.name)

    pk_clause = f"{' ' * 4}PRIMARY KEY ({', '.join(primary_keys)})"

    strict_clause = " STRICT" if STRICT_TABLES else ""
    create_sql = (
        f"CREATE TEMP TABLE IF NOT EXISTS {table_name} (\n"
        f"{',\n'.join(col_defs)},\n"
        f"\n{pk_clause}"
        f"\n){strict_clause};"
    )

    if wipe:
        script = create_sql + f"\nDELETE FROM {table_name};"
    else:
        script = create_sql

    cur = conn.cursor()
    cur.executescript(script)

    cols = ", ".join(col_names)
    placeholders = ", ".join("?" for _ in col_names)
    insert_sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders});"

    cur.executemany(insert_sql, rows)
