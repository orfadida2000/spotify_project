import sqlite3

from sp2genius.utils import err_msg

from .entities import Album, AlbumImage, Artist, ArtistImage, DiscographyEntry, Song


def _ensure_discography_entries(
    cur: sqlite3.Cursor,
    song: Song,
    artists: list[Artist],
) -> None:
    for artist in artists:
        artist.register_discography_entry(cur, song)


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
    _ensure_discography_entries(cur, song, all_artists)


def get_tracks_for_artist(
    conn: sqlite3.Connection,
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
        SELECT {DiscographyEntry.get_fk_names_to_entity(Song)}
        FROM {DiscographyEntry.TABLE_NAME}
        WHERE {DiscographyEntry.get_fk_names_to_entity(Artist)} = :aid
        """,
        {"aid": artist.get_id()},
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
    - Result is sorted by: main_artist_id, then album_id, then disc_number, then track_number.
    """
    assert isinstance(artists, list), err_msg("artists must be a list of Artist objects")
    if not artists:
        return []

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
            FROM {Song.TABLE_NAME}
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
