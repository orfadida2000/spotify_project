import sqlite3
from collections.abc import Sequence
from typing import Any

from sp2genius.utils.errors import err_msg

from ..core.sql.fragments import generate_order_by_clause
from ..core.sql.temp_table import SqlColType, init_temp_table
from ..core.sql.utils import get_effective_max_bind_params
from ..core.typing import TableColumn
from .entities import Album, AlbumImage, Artist, ArtistImage, DiscographyEntry, Song, SpotifyEntity


def _ensure_discography_entries(
    cur: sqlite3.Cursor,
    *,
    song: Song,
    artists: Sequence[Artist],
) -> None:
    for artist in artists:
        artist.register_discography_entry(cur, song)


# --- Public API: insert_song --------------------------------------------------
def insert_spotify_song(
    conn: sqlite3.Connection,
    *,
    song: Song,
    primary_artist: tuple[Artist, Sequence[ArtistImage]],
    album: tuple[Album, Sequence[AlbumImage]],
    featured_artists: Sequence[tuple[Artist, Sequence[ArtistImage]]],
) -> None:
    """
    Insert or patch a song, its main artist, album, and discography entries.
    For cases where no images (artist or album) exist pass an empty list for images.
    For featured artists, pass an empty list if none exist.
    - Keys we pass to helpers are column names: artist_id, name, album_id, title, etc.
    - Helpers will UPDATE first (patch existing row) and INSERT only if no row exists.
    """

    cur = conn.cursor()

    # 1. main artist (only set what we know)
    primary_artist_obj, primary_artist_images = primary_artist
    primary_artist_obj.upsert_to_db(cur)
    for artist_image in primary_artist_images:
        primary_artist_obj.register_image(cur, artist_image)

    feat_artist_objects = []
    # 2. featured artists (if provided)
    for feat_artist_obj, feat_artist_images in featured_artists:
        feat_artist_objects.append(feat_artist_obj)
        feat_artist_obj.upsert_to_db(cur)
        for artist_image in feat_artist_images:
            feat_artist_obj.register_image(cur, artist_image)

    all_artists = [primary_artist_obj] + feat_artist_objects

    # 3. album (patch or insert)
    album_obj, album_images = album
    if album_obj.get_id() != song.get_album_id():
        raise ValueError(err_msg("Song's album_id must match the provided album's album_id"))
    if album_obj.get_primary_artist_id() not in {artist.get_id() for artist in all_artists}:
        raise ValueError(
            err_msg("Album's primary_artist_id must match one of the provided artists' artist_id")
        )
    album_obj.upsert_to_db(cur)
    for album_image in album_images:
        album_obj.register_image(cur, album_image)

    # 4. song (patch or insert)
    if song.get_primary_artist_id() != primary_artist_obj.get_id():
        raise ValueError(
            err_msg("Song's primary_artist_id must match the provided primary artist's artist_id")
        )
    song.upsert_to_db(cur)

    # 5. discography entries: main artist + any featured artists
    _ensure_discography_entries(cur, song=song, artists=all_artists)


def get_tracks_for_artist(
    conn: sqlite3.Connection,
    *,
    artist: Artist,
    strict: bool = False,
) -> set[str]:
    cur = conn.cursor()

    if strict:
        if not artist.exists_in_db(cur):
            raise ValueError(
                err_msg(f"Artist '{artist.get_id()}' does not exist in table 'artists'.")
            )

    cur.execute(
        f"""
        SELECT {DiscographyEntry.get_song_id_col_name()}
        FROM {DiscographyEntry.get_table_name()}
        WHERE {DiscographyEntry.get_artist_id_col_name()} = :aid
        """,
        {"aid": artist.get_id()},
    )
    rows = cur.fetchall()
    return {row[0] for row in rows}


def get_joint_songs_for_artists(
    conn: sqlite3.Connection,
    *,
    artists: Sequence[Artist],
    strict: bool = False,
) -> list[sqlite3.Row]:
    """
    Given a list of artist_ids, return a list of sqlite3.Row objects representing
    songs that ALL of these artists participated in (intersection of their tracks).

    - Uses the discography table to find shared track_ids.
    - Then fetches full rows from the songs table.
    - Result is sorted by: main_artist_id, then album_id, then disc_number, then track_number.
    """
    assert isinstance(artists, Sequence), err_msg("artists must be a sequence of Artist objects")
    if not artists:
        return []

    # 1. Build the intersection of track IDs across all artists
    track_sets: list[set[str]] = []
    for artist in artists:
        tracks = get_tracks_for_artist(conn, artist=artist, strict=strict)
        track_sets.append(tracks)

    # Start with a copy of the first set, then intersect with the rest
    joint_tracks: set[str] = set(track_sets[0])
    for s in track_sets[1:]:
        joint_tracks.intersection_update(s)

    if not joint_tracks:
        return []

    # 2. Fetch full song rows for all intersecting track_ids, using sqlite3.Row
    track_list = list(joint_tracks)
    placeholders = ", ".join("?" for _ in track_list)

    cur = conn.cursor()
    cur.row_factory = sqlite3.Row  # type: ignore
    cur.execute(
        f"""
        SELECT *
        FROM {Song.get_table_name()}
        WHERE {Song.get_id_col_name()} IN ({placeholders})
        """,
        track_list,
    )
    songs = cur.fetchall()

    # 3. Sort by main_artist_id, then album_id, then title
    songs.sort(
        key=lambda song: (
            song[Song.get_primary_artist_id_col_name()],
            song[Song.get_album_id_col_name()],
            song[Song.get_disc_number_col_name()],
            song[Song.get_track_number_col_name()],
        )
    )

    return songs


def _prepare_temp_table_entity_ids(
    conn: sqlite3.Connection,
    *,
    entity_ids: set[str],
    entity_cls: type[SpotifyEntity],
) -> None:
    """
    Create (if needed) a STRICT temp table, wipe it, and insert entity_ids.
    """
    assert entity_ids, err_msg("entity_ids set cannot be empty")

    temp_columns = [
        TableColumn(
            name="id",
            sql_type=SqlColType.TEXT,
        ),
    ]
    pk_columns = (id_column_name,)
    id_rows = ((aid,) for aid in entity_ids)
    init_temp_table(
        conn,
        table_name=temp_table_name,
        columns=temp_columns,
        primary_keys=pk_columns,
        rows=id_rows,
    )


def _get_entity_ids_exists_in_db(
    conn: sqlite3.Connection,
    *,
    entity_ids: set[str],
    entity_cls: type[SpotifyEntity],
    sql_in_threshold: int = 100,
) -> set[str]:
    assert entity_ids, err_msg("entity_ids set cannot be empty")
    if not issubclass(entity_cls, SpotifyEntity):
        raise TypeError(err_msg("entity_cls must be a subclass of SpotifyEntity"))
    if not entity_cls.is_concrete_entity():
        raise TypeError(err_msg("entity_cls must be a concrete entity class"))

    effective_in_threshold = get_effective_max_bind_params(sql_in_threshold)
    n = len(entity_ids)

    cur = conn.cursor()

    # Case 1: n = 1
    if n == 1:
        eid = next(iter(entity_ids))
        cur.execute(
            f"""
            SELECT 1
            FROM {entity_cls.get_table_name()}
            WHERE {entity_cls.get_id_col_name()} = :eid
            """,
            {"eid": eid},
        )
        row = cur.fetchone()
        return {eid} if row else set()


def select_songs_including_all_artists(
    conn: sqlite3.Connection,
    *,
    artists: Sequence[Artist],
    sql_in_threshold: int = 100,
    order_by: bool = True,
    check_existence: bool = False,
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
    effective_in_threshold = get_effective_max_bind_params(sql_in_threshold)

    # Deduplicate once, globally
    dedup_artists: list[Artist] = []
    artist_ids: set[str] = set()
    for artist in artists:
        aid = artist.get_id()
        if aid not in artist_ids:
            dedup_artists.append(artist)
            artist_ids.add(aid)
    artists = dedup_artists

    n = len(artist_ids)

    # Case 1: empty after deduplication
    if n == 0:
        raise ValueError("artists list must contain at least one distinct artist id")

    cur = conn.cursor()
    cur.row_factory = sqlite3.Row  # type: ignore

    # Case 2: single artist
    if n == 1:
        artist = artists[0]
        return artist.get_all_songs(
            cur,
            order_by=order_by,
            check_existence=check_existence,
        )

    order_by_cols = Song.get_order_by_cols()
    order_clause = generate_order_by_clause("s", order_by_cols) if order_by else ""

    # Case 3: IN (...) for medium N
    if n <= effective_in_threshold:
        params: dict[str, Any] = {"n_artists": n}
        placeholders: list[str] = []

        for i, aid in enumerate(artist_ids, start=1):
            k = f"a{i}"
            params[k] = aid
            placeholders.append(f":{k}")

        sql = f"""
            SELECT s.*
            FROM {Song.get_table_name()} AS s
            JOIN (
                SELECT d.{DiscographyEntry.get_song_id_col_name()}
                FROM {DiscographyEntry.get_table_name()} AS d
                WHERE d.{DiscographyEntry.get_artist_id_col_name()} IN ({", ".join(placeholders)})
                GROUP BY d.{DiscographyEntry.get_song_id_col_name()}
                HAVING COUNT(DISTINCT d.{DiscographyEntry.get_artist_id_col_name()}) = :n_artists
            ) AS t
              ON t.{DiscographyEntry.get_song_id_col_name()} = s.{Song.get_id_col_name()}
            {order_clause};
        """
        cur.execute(sql, params)
        return cur.fetchall()

    # Case 4: temp table for large N
    temp_artist_ids_table_name = "temp_spotify_artist_ids"
    temp_artist_id_col_name = Artist.get_id_col_name()
    _prepare_temp_table_entity_ids(
        conn,
        entity_ids=artist_ids,
        temp_table_name=temp_artist_ids_table_name,
        id_column_name=temp_artist_id_col_name,
    )
    inserted_n = len(artist_ids)

    sql = f"""
        SELECT s.*
        FROM {Song.get_table_name()} AS s
        JOIN (
            SELECT d.{DiscographyEntry.get_song_id_col_name()}
            FROM {DiscographyEntry.get_table_name()} AS d
            JOIN {temp_artist_ids_table_name} AS a
              ON a.{temp_artist_id_col_name} = d.{DiscographyEntry.get_artist_id_col_name()}
            GROUP BY d.{DiscographyEntry.get_song_id_col_name()}
            HAVING COUNT(DISTINCT d.{DiscographyEntry.get_artist_id_col_name()}) = :n_artists
        ) AS t
          ON t.{DiscographyEntry.get_song_id_col_name()} = s.{Song.get_id_col_name()}
        {order_clause};
    """
    cur.execute(sql, {"n_artists": inserted_n})
    return cur.fetchall()
