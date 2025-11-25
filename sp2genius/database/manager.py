import sqlite3

from .entities import Album, AlbumImage, Artist, ArtistImage, DiscographyEntry, Song
from .schema import (
    ALBUMS_TABLE_PRIMARY_KEYS,
    ARTISTS_TABLE_PRIMARY_KEYS,
    FOREIGN_KEYS,
    FULL_SCHEMA,
    SONGS_TABLE_PRIMARY_KEYS,
)


def initialize_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f"PRAGMA foreign_keys = {'ON' if FOREIGN_KEYS else 'OFF'};")
        conn.executescript(FULL_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# --- Upsert helpers using UPDATE-then-INSERT with dynamic columns -------------


def _upsert_artist(cur: sqlite3.Cursor, data: dict) -> None:
    """
    data must contain: artist_id
    Optional: name
    """
    for pk_col in ARTISTS_TABLE_PRIMARY_KEYS:
        if pk_col not in data:
            raise ValueError(f"_upsert_artist: '{pk_col}' is required in data")

    update_cols = [k for k in data.keys() if k not in ARTISTS_TABLE_PRIMARY_KEYS]
    # 1) Try UPDATE (patch existing row)
    if update_cols:
        where_clause = " AND ".join(
            f"{pk_col} = :{pk_col}" for pk_col in ARTISTS_TABLE_PRIMARY_KEYS
        )
        set_clause = ", ".join(f"{col} = :{col}" for col in update_cols)
        sql = f"UPDATE artists SET {set_clause} WHERE {where_clause}"
        cur.execute(sql, data)
        if cur.rowcount > 0:
            return  # row existed and has been patched

    # 2) If no row was updated, try INSERT with the provided columns
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{col}" for col in data.keys())
    sql = f"INSERT INTO artists ({cols}) VALUES ({placeholders})"
    cur.execute(sql, data)


def _upsert_album(cur: sqlite3.Cursor, data: dict[str, str]) -> None:
    """
    data must contain: album_id
    Optional: title, main_artist_id, album_type
    """
    for pk_col in ALBUMS_TABLE_PRIMARY_KEYS:
        if pk_col not in data:
            raise ValueError(f"_upsert_album: '{pk_col}' is required in data")

    update_cols = [k for k in data.keys() if k not in ALBUMS_TABLE_PRIMARY_KEYS]
    # 1) UPDATE existing row (patch)
    if update_cols:
        set_clause = ", ".join(f"{col} = :{col}" for col in update_cols)
        where_clause = " AND ".join(f"{pk_col} = :{pk_col}" for pk_col in ALBUMS_TABLE_PRIMARY_KEYS)
        sql = f"UPDATE albums SET {set_clause} WHERE {where_clause}"
        cur.execute(sql, data)
        if cur.rowcount > 0:
            return

    # 2) INSERT new row with provided columns
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{col}" for col in data.keys())
    sql = f"INSERT INTO albums ({cols}) VALUES ({placeholders})"
    cur.execute(sql, data)


def _upsert_song(cur: sqlite3.Cursor, data: dict[str, str | None]) -> None:
    """
    data must contain: track_id
    Optional: title, genius_url, main_artist_id, album_id
    """
    for pk_col in SONGS_TABLE_PRIMARY_KEYS:
        if pk_col not in data:
            raise ValueError(f"_upsert_song: '{pk_col}' is required in data")

    update_cols = [k for k in data.keys() if k not in SONGS_TABLE_PRIMARY_KEYS]
    # 1) UPDATE existing row (patch)
    if update_cols:
        set_clause = ", ".join(f"{col} = :{col}" for col in update_cols)
        where_clause = " AND ".join(f"{pk_col} = :{pk_col}" for pk_col in SONGS_TABLE_PRIMARY_KEYS)
        sql = f"UPDATE songs SET {set_clause} WHERE {where_clause}"
        cur.execute(sql, data)
        if cur.rowcount > 0:
            return

    # 2) INSERT new row with provided columns
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{col}" for col in data.keys())
    sql = f"INSERT INTO songs ({cols}) VALUES ({placeholders})"
    cur.execute(sql, data)


def _ensure_discography_entries(
    cur: sqlite3.Cursor,
    song: Song,
    artists: list[Artist],
) -> None:
    for artist in artists:
        data = {
            "track_id": song.track_id,  # type: ignore
            "artist_id": artist.artist_id,  # type: ignore
        }
        entry = DiscographyEntry(data)
        entry.insert_to_db(cur)


# --- Public API: insert_song --------------------------------------------------


def insert_song(
    conn: sqlite3.Connection,
    *,
    song: Song,
    primary_artist: tuple[Artist, list[ArtistImage]],
    album: tuple[Album, list[AlbumImage]],
    featured_artists: list[tuple[Artist, list[ArtistImage]]],
) -> None:
    """
    Insert or patch a song, its main artist, album, and discography entries.

    - Keys we pass to helpers are column names: artist_id, name, album_id, title, etc.
    - Helpers will UPDATE first (patch existing row) and INSERT only if no row exists.
    """
    conn.execute(f"PRAGMA foreign_keys = {'ON' if FOREIGN_KEYS else 'OFF'};")
    cur = conn.cursor()
    try:
        cur.execute("BEGIN;")

        # 1. main artist (only set what we know)
        primary_artist_obj, primary_artist_images = primary_artist
        primary_artist_obj.upsert_to_db(cur)
        for artist_image in primary_artist[1]:
            if artist_image.artist_id != primary_artist_obj.artist_id:  # type: ignore
                raise ValueError("An image attached to an artist must reference its artist_id")
            artist_image.upsert_to_db(cur)

        feat_artist_objects = []
        # 2. featured artists (if provided)
        for feat_artist_obj, feat_artist_images in featured_artists:
            feat_artist_objects.append(feat_artist_obj)
            feat_artist_obj.upsert_to_db(cur)
            for artist_image in feat_artist_images:
                if artist_image.artist_id != feat_artist_obj.artist_id:  # type: ignore
                    raise ValueError("An image attached to an artist must reference its artist_id")
                artist_image.upsert_to_db(cur)

        # 3. album (patch or insert)
        album_obj, album_images = album
        album_obj.upsert_to_db(cur)
        for album_image in album_images:
            if album_image.album_id != album_obj.album_id:  # type: ignore
                raise ValueError("An image attached to an album must reference its album_id")
            album_image.upsert_to_db(cur)

        # 4. song (patch or insert)
        song.upsert_to_db(cur)

        # 5. discography entries: main artist + any featured artists
        all_artists = [primary_artist_obj] + feat_artist_objects

        _ensure_discography_entries(cur, song, all_artists)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e


def get_tracks_for_artist(
    conn: sqlite3.Connection,
    artist: Artist,
    strict: bool = False,
) -> set[str]:
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    if strict:
        if not artist.exists_in_db(cur):
            raise ValueError(f"Artist '{artist.artist_id}' does not exist in table 'artists'.")  # type: ignore

    cur.execute(
        """
        SELECT track_id
        FROM discography
        WHERE artist_id = :aid
        """,
        {"aid": artist.artist_id},  # type: ignore
    )
    rows = cur.fetchall()
    return {row[0] for row in rows}


def get_joint_songs_for_artists(
    conn: sqlite3.Connection,
    artists: list[Artist],
    strict: bool = False,
) -> list[sqlite3.Row]:
    """
    Given a list of artist_ids, return a list of sqlite3.Row objects representing
    songs that ALL of these artists participated in (intersection of their tracks).

    - Uses the discography table to find shared track_ids.
    - Then fetches full rows from the songs table.
    - Result is sorted by: main_artist_id, then album_id, then title.
    """
    assert isinstance(artists, list), "artists must be a list of Artist objects"
    if not artists:
        return []

    conn.execute("PRAGMA foreign_keys = ON;")

    # 1. Build the intersection of track IDs across all artists
    track_sets: list[set[str]] = []
    for artist in artists:
        tracks = get_tracks_for_artist(conn, artist, strict=strict)
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

    old_row_factory = conn.row_factory
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT *
            FROM songs
            WHERE track_id IN ({placeholders})
            """,
            track_list,
        )
        songs = cur.fetchall()
    finally:
        conn.row_factory = old_row_factory

    # 3. Sort by main_artist_id, then album_id, then title
    songs.sort(
        key=lambda song: (
            song["primary_artist_id"],
            song["album_id"],
            song["disc_number"],
            song["track_number"],
        )
    )

    return songs
