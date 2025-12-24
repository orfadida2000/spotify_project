import sqlite3

from sp2genius.utils import err_msg

from .entities import GeniusAlbumInfo, GeniusArtistInfo, GeniusDiscographyEntry, GeniusSongInfo


def _ensure_discography_entries(
    cur: sqlite3.Cursor,
    song: GeniusSongInfo,
    artists: list[GeniusArtistInfo],
) -> None:
    for artist in artists:
        artist.register_discography_entry(cur, song)


# --- Public API: insert_song --------------------------------------------------
def insert_genius_song_info(
    conn: sqlite3.Connection,
    *,
    song: GeniusSongInfo,
    primary_artist: GeniusArtistInfo,
    album: GeniusAlbumInfo,
    featured_artists: list[GeniusArtistInfo],
) -> None:
    """
    Insert or patch a song, its main artist, album, and discography entries.
    For featured artists, pass an empty list if none exist.
    """

    cur = conn.cursor()

    # 1. main artist (only set what we know)
    primary_artist.upsert_to_db(cur)

    # 2. featured artists (if provided)
    for feat_artist in featured_artists:
        feat_artist.upsert_to_db(cur)

    all_artists = [primary_artist] + featured_artists

    # 3. album (patch or insert)
    if album.get_id() != song.get_album_id():
        raise ValueError(
            err_msg("Song's album_genius_id must match the provided album's genius_id")
        )
    if album.get_primary_artist_id() not in {artist.get_id() for artist in all_artists}:
        raise ValueError(
            err_msg(
                "Album's primary_artist_genius_id must match one of the provided artists' genius_id"
            )
        )
    album.upsert_to_db(cur)

    # 4. song (patch or insert)
    if song.get_primary_artist_id() != primary_artist.get_id():
        raise ValueError(
            err_msg(
                "Song's primary_artist_genius_id must match the provided primary artist's genius_id"
            )
        )
    song.upsert_to_db(cur)

    # 5. discography entries: main artist + any featured artists
    _ensure_discography_entries(cur, song, all_artists)


def get_songs_for_artist(
    conn: sqlite3.Connection,
    artist: GeniusArtistInfo,
    strict: bool = False,
) -> set[str]:
    cur = conn.cursor()

    if strict:
        if not artist.exists_in_db(cur):
            raise ValueError(
                err_msg(
                    f"Artist '{artist.get_id()}' does not exist in table '{GeniusArtistInfo.TABLE_NAME}'."
                )
            )

    cur.execute(
        f"""
        SELECT {GeniusDiscographyEntry.get_song_id_col_name()}
        FROM {GeniusDiscographyEntry.TABLE_NAME}
        WHERE {GeniusDiscographyEntry.get_artist_id_col_name()} = :aid
        """,
        {"aid": artist.get_id()},
    )
    rows = cur.fetchall()
    return {row[0] for row in rows}


def get_joint_songs_for_artists(
    conn: sqlite3.Connection,
    artists: list[GeniusArtistInfo],
    strict: bool = False,
) -> list[sqlite3.Row]:
    """
    Given a list of artist_ids, return a list of sqlite3.Row objects representing
    songs that ALL of these artists participated in (intersection of their songs).

    - Uses the discography table to find shared song_ids.
    - Then fetches full rows from the songs table.
    - Result is sorted by: main_artist_id, then album_id, then title.
    """
    assert isinstance(artists, list), err_msg("artists must be a list of Artist objects")
    if not artists:
        return []

    # 1. Build the intersection of song IDs across all artists
    song_sets: list[set[str]] = []
    for artist in artists:
        songs = get_songs_for_artist(conn, artist, strict=strict)
        song_sets.append(songs)

    # Start with a copy of the first set, then intersect with the rest
    joint_songs: set[str] = set(song_sets[0])
    for s in song_sets[1:]:
        joint_songs.intersection_update(s)

    if not joint_songs:
        return []

    # 2. Fetch full song rows for all intersecting song_ids, using sqlite3.Row
    song_list = list(joint_songs)
    placeholders = ", ".join("?" for _ in song_list)

    cur = conn.cursor()
    cur.row_factory = sqlite3.Row  # type: ignore
    cur.execute(
        f"""
        SELECT *
        FROM {GeniusSongInfo.TABLE_NAME}
        WHERE {GeniusSongInfo.get_id_col_name()} IN ({placeholders})
        """,
        song_list,
    )
    songs = cur.fetchall()

    # 3. Sort by main_artist_id, then album_id, then title
    songs.sort(
        key=lambda song: (
            song[GeniusSongInfo.get_primary_artist_id_col_name()],
            song[GeniusSongInfo.get_album_id_col_name()],
            song[GeniusSongInfo.get_title_col_name()],
        )
    )

    return songs
