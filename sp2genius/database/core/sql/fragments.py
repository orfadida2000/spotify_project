from collections.abc import Sequence

from .utils import sanitize_sql_identifier


def generate_order_by_clause(table_ref: str, cols: Sequence[str]) -> str:
    assert isinstance(cols, Sequence), "cols must be a sequence"
    sanitized_table_ref = sanitize_sql_identifier(table_ref, strict=True)
    sanitized_cols = [sanitize_sql_identifier(col, strict=True) for col in cols]

    if not sanitized_cols:
        return ""

    order_by_parts = [f"{sanitized_table_ref}.{col}" for col in sanitized_cols]
    order_by_clause = "ORDER BY " + ", ".join(order_by_parts)
    return order_by_clause
