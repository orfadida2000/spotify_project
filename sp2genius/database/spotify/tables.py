from typing import Final

from ..core.constants import CONCAT
from ..core.typing import (
    CreateStatement,
    FieldMeta,
    ForeignKeyMapping,
    PrimaryKeyNames,
    TableMeta,
    TableName,
)
from ..core.utils import (
    CHECK_ALPHANUMERIC_GLOB,
    CHECK_ISO_FULL_DATE_GLOB,
    CHECK_ISO_YEAR_GLOB,
    CHECK_ISO_YEAR_MONTH_GLOB,
)
from ..genius.tables import (
    GENIUS_ALBUM_INFO_TABLE_NAME,
    GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_ARTIST_INFO_TABLE_NAME,
    GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_SONG_INFO_TABLE_NAME,
    GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS,
)


# ---- UTILS ---- #
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


def CHECK_SPOTIFY_ID_GLOB(id: str) -> str:  # noqa: N802
    return f"length({id}) = 22 AND {CHECK_ALPHANUMERIC_GLOB(col=id)}"


# ---- SPOTIFY TABLES + EXTENDED METADATA ---- #

# Artists Table
ARTISTS_TABLE_NAME: Final[TableName] = "artists"
ARTISTS_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {ARTISTS_TABLE_NAME} (
    artist_id       TEXT PRIMARY KEY
                        CHECK ({CHECK_SPOTIFY_ID_GLOB(id="artist_id")}),
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
        REFERENCES {GENIUS_ARTIST_INFO_TABLE_NAME}({GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE SET NULL
) STRICT;
"""
ARTISTS_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("artist_id",)
ARTISTS_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_ARTIST_INFO_TABLE_NAME: {
        GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]: "genius_id",
    },
}
ARTISTS_TABLE_META: Final[TableMeta] = {
    "artist_id": FieldMeta(py_type=str, nullable=False),
    "name": FieldMeta(py_type=str, nullable=False),
    "genius_id": FieldMeta(py_type=int, nullable=True),
    "total_followers": FieldMeta(py_type=int, nullable=True),
    "genres": FieldMeta(py_type=str, nullable=True),
    "popularity": FieldMeta(py_type=int, nullable=True),
}

# Albums Table
ALBUMS_TABLE_NAME: Final[TableName] = "albums"
ALBUMS_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {ALBUMS_TABLE_NAME} (
    album_id               TEXT PRIMARY KEY
                               CHECK ({CHECK_SPOTIFY_ID_GLOB(id="album_id")}),
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
        REFERENCES {GENIUS_ALBUM_INFO_TABLE_NAME}({GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE SET NULL,

    FOREIGN KEY (primary_artist_id)
        REFERENCES {ARTISTS_TABLE_NAME}({ARTISTS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT
) STRICT;
"""
ALBUMS_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("album_id",)
ALBUMS_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_ALBUM_INFO_TABLE_NAME: {
        GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS[0]: "genius_id",
    },
    ARTISTS_TABLE_NAME: {
        ARTISTS_TABLE_PRIMARY_KEYS[0]: "primary_artist_id",
    },
}
ALBUMS_TABLE_META: Final[TableMeta] = {
    "album_id": FieldMeta(py_type=str, nullable=False),
    "title": FieldMeta(py_type=str, nullable=False),
    "genius_id": FieldMeta(py_type=int, nullable=True),
    "primary_artist_id": FieldMeta(py_type=str, nullable=False),
    "album_type": FieldMeta(py_type=str, nullable=False),
    "total_tracks": FieldMeta(py_type=int, nullable=False),
    "release_date": FieldMeta(py_type=str, nullable=False),
    "label": FieldMeta(py_type=str, nullable=True),
    "popularity": FieldMeta(py_type=int, nullable=True),
}

# Songs Table
SONGS_TABLE_NAME: Final[TableName] = "songs"
SONGS_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {SONGS_TABLE_NAME} (
    track_id          TEXT PRIMARY KEY
                          CHECK ({CHECK_SPOTIFY_ID_GLOB(id="track_id")}),
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
        REFERENCES {GENIUS_SONG_INFO_TABLE_NAME}({GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE SET NULL,

    FOREIGN KEY (primary_artist_id)
        REFERENCES {ARTISTS_TABLE_NAME}({ARTISTS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT,

    FOREIGN KEY (album_id)
        REFERENCES {ALBUMS_TABLE_NAME}({ALBUMS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT
) STRICT;
"""
SONGS_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("track_id",)
SONGS_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_SONG_INFO_TABLE_NAME: {
        GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS[0]: "genius_id",
    },
    ARTISTS_TABLE_NAME: {
        ARTISTS_TABLE_PRIMARY_KEYS[0]: "primary_artist_id",
    },
    ALBUMS_TABLE_NAME: {
        ALBUMS_TABLE_PRIMARY_KEYS[0]: "album_id",
    },
}
SONGS_TABLE_META: Final[TableMeta] = {
    "track_id": FieldMeta(py_type=str, nullable=False),
    "title": FieldMeta(py_type=str, nullable=False),
    "genius_id": FieldMeta(py_type=int, nullable=True),
    "primary_artist_id": FieldMeta(py_type=str, nullable=False),
    "album_id": FieldMeta(py_type=str, nullable=False),
    "disc_number": FieldMeta(py_type=int, nullable=False),
    "track_number": FieldMeta(py_type=int, nullable=False),
    "duration_ms": FieldMeta(py_type=int, nullable=False),
    "explicit": FieldMeta(py_type=bool, nullable=False),
    "popularity": FieldMeta(py_type=int, nullable=False),
}

# Discography Table
DISCOGRAPHY_TABLE_NAME: Final[TableName] = "discography"
DISCOGRAPHY_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {DISCOGRAPHY_TABLE_NAME} (
    artist_id TEXT NOT NULL,
    track_id  TEXT NOT NULL,

    PRIMARY KEY (artist_id, track_id),

    FOREIGN KEY (artist_id)
        REFERENCES {ARTISTS_TABLE_NAME}({ARTISTS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT,

    FOREIGN KEY (track_id)
        REFERENCES {SONGS_TABLE_NAME}({SONGS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE CASCADE
) STRICT;
"""
DISCOGRAPHY_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("artist_id", "track_id")
DISCOGRAPHY_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    ARTISTS_TABLE_NAME: {
        ARTISTS_TABLE_PRIMARY_KEYS[0]: "artist_id",
    },
    SONGS_TABLE_NAME: {
        SONGS_TABLE_PRIMARY_KEYS[0]: "track_id",
    },
}
DISCOGRAPHY_TABLE_META: Final[TableMeta] = {
    "artist_id": FieldMeta(py_type=str, nullable=False),
    "track_id": FieldMeta(py_type=str, nullable=False),
}

# Artist Images Table
ARTIST_IMAGES_TABLE_NAME: Final[TableName] = "artist_images"
ARTIST_IMAGES_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {ARTIST_IMAGES_TABLE_NAME} (
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
        REFERENCES {ARTISTS_TABLE_NAME}({ARTISTS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE CASCADE
) STRICT;
"""
ARTIST_IMAGES_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("artist_id", "url")
ARTIST_IMAGES_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    ARTISTS_TABLE_NAME: {
        ARTISTS_TABLE_PRIMARY_KEYS[0]: "artist_id",
    },
}
ARTIST_IMAGES_TABLE_META: Final[TableMeta] = {
    "artist_id": FieldMeta(py_type=str, nullable=False),
    "url": FieldMeta(py_type=str, nullable=False),
    "width": FieldMeta(py_type=int, nullable=True),
    "height": FieldMeta(py_type=int, nullable=True),
}

# Album Images Table
ALBUM_IMAGES_TABLE_NAME: Final[TableName] = "album_images"
ALBUM_IMAGES_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {ALBUM_IMAGES_TABLE_NAME} (
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
        REFERENCES {ALBUMS_TABLE_NAME}({ALBUMS_TABLE_PRIMARY_KEYS[0]})
        ON DELETE CASCADE
) STRICT;
"""
ALBUM_IMAGES_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("album_id", "url")
ALBUM_IMAGES_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    ALBUMS_TABLE_NAME: {
        ALBUMS_TABLE_PRIMARY_KEYS[0]: "album_id",
    },
}
ALBUM_IMAGES_TABLE_META: Final[TableMeta] = {
    "album_id": FieldMeta(py_type=str, nullable=False),
    "url": FieldMeta(py_type=str, nullable=False),
    "width": FieldMeta(py_type=int, nullable=True),
    "height": FieldMeta(py_type=int, nullable=True),
}

# All Tables Creation Statements in Order of Dependencies
TABLES: Final[list[CreateStatement]] = [
    ARTISTS_TABLE,
    ALBUMS_TABLE,
    SONGS_TABLE,
    DISCOGRAPHY_TABLE,
    ARTIST_IMAGES_TABLE,
    ALBUM_IMAGES_TABLE,
]
