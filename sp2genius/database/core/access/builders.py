import sqlite3
from collections.abc import Sequence
from typing import Any, Protocol

from ..sql.temp_table import SqlColType, init_temp_table
from ..typing import TableColumn


class _HasGetId(Protocol):
    def get_id(self) -> str: ...


_TEMP_TABLE_NAME = "temp_artist_ids"


def _prepare_temp_artist_ids(
    conn: sqlite3.Connection,
    artist_ids: set[str],
) -> int:
    """
    Create (if needed) a STRICT temp table, wipe it, and insert artist_ids.

    Returns:
        int: number of distinct artist IDs inserted.
    """
    temp_columns = [
        TableColumn(
            name="artist_id",
            sql_type=SqlColType.TEXT,
        ),
    ]
    pk_columns = ("artist_id",)
    id_rows = ((aid,) for aid in artist_ids)
    init_temp_table(
        conn,
        table_name=_TEMP_TABLE_NAME,
        columns=temp_columns,
        primary_keys=pk_columns,
        rows=id_rows,
    )
    return len(artist_ids)


def select_songs_including_all_artists(
    conn: sqlite3.Connection,
    *,
    artists: Sequence[_HasGetId],
    n_in_threshold: int = 100,
    order_by: bool = True,
) -> list[sqlite3.Row]:
    """
    Select all songs that include *all* given artists (based on discography).

    Cases:
      1) empty list -> error
      2) N == 1 -> simple query
      3) 2 <= N <= n_in_threshold -> IN (...) + GROUP BY/HAVING
      4) N > n_in_threshold -> TEMP STRICT table + GROUP BY/HAVING
    """
    if not artists:
        raise ValueError("artists list must be non-empty")

    # Deduplicate once, globally
    artist_ids: set[str] = {a.get_id() for a in artists}

    n = len(artist_ids)
    if n == 0:
        raise ValueError("artists list must contain at least one distinct artist id")

    order_clause = "ORDER BY s.primary_artist_id, s.album_id, s.name" if order_by else ""

    # Case 2: single artist
    if n == 1:
        (aid,) = artist_ids
        sql = f"""
            SELECT s.*
            FROM songs AS s
            JOIN discography AS d
              ON d.track_id = s.track_id
            WHERE d.artist_id = :a1
            {order_clause};
        """
        cur = conn.execute(sql, {"a1": aid})
        return cur.fetchall()

    # Case 3: IN (...) for medium N
    if n <= n_in_threshold:
        params: dict[str, Any] = {"n_artists": n}
        placeholders: list[str] = []

        for i, aid in enumerate(artist_ids, start=1):
            k = f"a{i}"
            params[k] = aid
            placeholders.append(f":{k}")

        sql = f"""
            SELECT s.*
            FROM songs AS s
            JOIN (
                SELECT d.track_id
                FROM discography AS d
                WHERE d.artist_id IN ({", ".join(placeholders)})
                GROUP BY d.track_id
                HAVING COUNT(DISTINCT d.artist_id) = :n_artists
            ) AS t
              ON t.track_id = s.track_id
            {order_clause};
        """
        cur = conn.execute(sql, params)
        return cur.fetchall()

    # Case 4: temp table for large N
    inserted_n = _prepare_temp_artist_ids(conn, artist_ids)

    sql = f"""
        SELECT s.*
        FROM songs AS s
        JOIN (
            SELECT d.track_id
            FROM discography AS d
            JOIN {_TEMP_TABLE_NAME} AS a
              ON a.artist_id = d.artist_id
            GROUP BY d.track_id
            HAVING COUNT(DISTINCT d.artist_id) = :n_artists
        ) AS t
          ON t.track_id = s.track_id
        {order_clause};
    """
    cur = conn.execute(sql, {"n_artists": inserted_n})
    return cur.fetchall()
