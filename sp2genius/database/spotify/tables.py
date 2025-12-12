from ..core import (
    CHECK_ALPHANUMERIC_GLOB,
    CHECK_ISO_FULL_DATE_GLOB,
    CHECK_ISO_YEAR_GLOB,
    CHECK_ISO_YEAR_MONTH_GLOB,
    CONCAT,
)


def _spotify_track_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/track/' {concat} {column}"


def _spotify_artist_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/artist/' {concat} {column}"


def _spotify_album_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/album/' {concat} {column}"


def spotify_id_to_url(column: str, concat: str, entity: str) -> str:
    if entity == "track":
        return _spotify_track_id_to_url(column, concat)
    elif entity == "artist":
        return _spotify_artist_id_to_url(column, concat)
    elif entity == "album":
        return _spotify_album_id_to_url(column, concat)
    else:
        raise ValueError(f"Unknown entity type: {entity}")


CHECK_ID_GLOB = lambda id: f"length({id}) = 22 AND {CHECK_ALPHANUMERIC_GLOB(col=id)}"

ARTISTS_TABLE = f"""
CREATE TABLE IF NOT EXISTS artists (
    artist_id       TEXT PRIMARY KEY
                        CHECK ({CHECK_ID_GLOB(id="artist_id")}),
    name            TEXT NOT NULL
                        CHECK (name <> ''),
    genius_id       INTEGER
                        CHECK (genius_id IS NULL OR genius_id > 0),
    total_followers INTEGER
                        CHECK (total_followers IS NULL OR total_followers >= 0),
    genres          TEXT
                        CHECK (genres IS NULL OR genres <> ''),
    popularity      INTEGER
                        CHECK (popularity IS NULL OR (popularity >= 0 AND popularity <= 100)),
    spotify_url     TEXT GENERATED ALWAYS AS (
                        {spotify_id_to_url(column="artist_id", concat=CONCAT, entity="artist")}
                    ) VIRTUAL,
    
    FOREIGN KEY (genius_id)
        REFERENCES genius_artist_info(genius_id)
        ON DELETE SET NULL
);
"""
ARTISTS_TABLE_PRIMARY_KEYS = ("artist_id",)
ARTISTS_TABLE_COL_META = {
    "artist_id": (True, str),
    "name": (True, str),
    "genius_id": (False, int),
    "total_followers": (False, int),
    "genres": (False, str),
    "popularity": (False, int),
}

# --- Date format constants -----------------------------------------------------

ALBUMS_TABLE = f"""
CREATE TABLE IF NOT EXISTS albums (
    album_id               TEXT PRIMARY KEY
                               CHECK ({CHECK_ID_GLOB(id="album_id")}),
    title                  TEXT NOT NULL
                               CHECK (title <> ''),
    genius_id              INTEGER
                               CHECK (genius_id IS NULL OR genius_id > 0),
    primary_artist_id      TEXT NOT NULL,
    album_type             TEXT NOT NULL
                               CHECK (album_type IN ('album', 'single', 'compilation')),
    total_tracks           INTEGER NOT NULL
                               CHECK (total_tracks > 0),
    release_date           TEXT NOT NULL
                               CHECK (
                                   ({CHECK_ISO_YEAR_GLOB(col="release_date")})
                                   OR ({CHECK_ISO_YEAR_MONTH_GLOB(col="release_date")})
                                   OR ({CHECK_ISO_FULL_DATE_GLOB(col="release_date")})
                               ),
    release_date_precision TEXT GENERATED ALWAYS AS (
                               CASE
                                   WHEN length(release_date) = 4  THEN 'year'
                                   WHEN length(release_date) = 7  THEN 'month'
                                   WHEN length(release_date) = 10 THEN 'day'
                               END
                           ) VIRTUAL,
    label                  TEXT
                               CHECK (label IS NULL OR label <> ''),
    popularity             INTEGER
                               CHECK (popularity IS NULL OR (popularity >= 0 AND popularity <= 100)),
    spotify_url            TEXT GENERATED ALWAYS AS (
                               {spotify_id_to_url(column="album_id", concat=CONCAT, entity="album")}
                           ) VIRTUAL,

    FOREIGN KEY (genius_id)
        REFERENCES genius_album_info(genius_id)
        ON DELETE SET NULL,

    FOREIGN KEY (primary_artist_id)
        REFERENCES artists(artist_id)
        ON DELETE RESTRICT
);
"""
ALBUMS_TABLE_PRIMARY_KEYS = ("album_id",)
ALBUMS_TABLE_COL_META = {
    "album_id": (True, str),
    "title": (True, str),
    "genius_id": (False, int),
    "primary_artist_id": (True, str),
    "album_type": (True, str),
    "total_tracks": (True, int),
    "release_date": (True, str),
    "label": (False, str),
    "popularity": (False, int),
}

SONGS_TABLE = f"""
CREATE TABLE IF NOT EXISTS songs (
    track_id          TEXT PRIMARY KEY
                          CHECK ({CHECK_ID_GLOB(id="track_id")}),
    title             TEXT NOT NULL
                          CHECK (title <> ''),
    genius_id         INTEGER
                          CHECK (genius_id IS NULL OR genius_id > 0),
    primary_artist_id TEXT NOT NULL,
    album_id          TEXT NOT NULL,
    disc_number       INTEGER NOT NULL
                          CHECK (disc_number > 0),
    track_number      INTEGER NOT NULL
                          CHECK (track_number > 0),
    duration_ms       INTEGER NOT NULL
                          CHECK (duration_ms > 0),
    explicit          INTEGER NOT NULL
                          CHECK (explicit IN (0, 1)),
    popularity        INTEGER NOT NULL
                          CHECK (popularity >= 0 AND popularity <= 100),
    spotify_url       TEXT GENERATED ALWAYS AS (
                          {spotify_id_to_url(column="track_id", concat=CONCAT, entity="track")}
                      ) VIRTUAL,

    FOREIGN KEY (genius_id)
        REFERENCES genius_song_info(genius_id)
        ON DELETE SET NULL,

    FOREIGN KEY (primary_artist_id)
        REFERENCES artists (artist_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (album_id)
        REFERENCES albums (album_id)
        ON DELETE RESTRICT
);
"""
SONGS_TABLE_PRIMARY_KEYS = ("track_id",)
SONGS_TABLE_COL_META = {
    "track_id": (True, str),
    "title": (True, str),
    "genius_id": (False, int),
    "primary_artist_id": (True, str),
    "album_id": (True, str),
    "disc_number": (True, int),
    "track_number": (True, int),
    "duration_ms": (True, int),
    "explicit": (True, bool),
    "popularity": (True, int),
}

DISCOGRAPHY_TABLE = """
CREATE TABLE IF NOT EXISTS discography (
    artist_id TEXT NOT NULL,
    track_id  TEXT NOT NULL,

    PRIMARY KEY (artist_id, track_id),

    FOREIGN KEY (artist_id)
        REFERENCES artists (artist_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (track_id)
        REFERENCES songs (track_id)
        ON DELETE CASCADE
);
"""
DISCOGRAPHY_TABLE_PRIMARY_KEYS = ("artist_id", "track_id")
DISCOGRAPHY_TABLE_COL_META = {
    "artist_id": (True, str),
    "track_id": (True, str),
}

ARTIST_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS artist_images (
    artist_id TEXT NOT NULL,
    url       TEXT NOT NULL
                  CHECK (url <> ''),
    width     INTEGER,
    height    INTEGER,

    PRIMARY KEY (artist_id, url),

    CHECK (
        (width IS NULL AND height IS NULL)
        OR (width IS NOT NULL AND width > 0 AND height IS NOT NULL AND height > 0)
    ),

    FOREIGN KEY (artist_id)
        REFERENCES artists (artist_id)
        ON DELETE CASCADE
);
"""
ARTIST_IMAGES_TABLE_PRIMARY_KEYS = ("artist_id", "url")
ARTIST_IMAGES_TABLE_COL_META = {
    "artist_id": (True, str),
    "url": (True, str),
    "width": (False, int),
    "height": (False, int),
}

ALBUM_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS album_images (
    album_id  TEXT NOT NULL,
    url       TEXT NOT NULL
                  CHECK (url <> ''),
    width     INTEGER,
    height    INTEGER,

    PRIMARY KEY (album_id, url),

    CHECK (
        (width IS NULL AND height IS NULL)
        OR (width IS NOT NULL AND width > 0 AND height IS NOT NULL AND height > 0)
    ),

    FOREIGN KEY (album_id)
        REFERENCES albums (album_id)
        ON DELETE CASCADE
);
"""
ALBUM_IMAGES_TABLE_PRIMARY_KEYS = ("album_id", "url")
ALBUM_IMAGES_TABLE_COL_META = {
    "album_id": (True, str),
    "url": (True, str),
    "width": (False, int),
    "height": (False, int),
}


TABLES = [
    ARTISTS_TABLE,
    ALBUMS_TABLE,
    SONGS_TABLE,
    DISCOGRAPHY_TABLE,
    ARTIST_IMAGES_TABLE,
    ALBUM_IMAGES_TABLE,
]
