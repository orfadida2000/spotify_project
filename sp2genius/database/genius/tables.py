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
from ..core.utils import CHECK_BASE64_URL_SAFE_GLOB, CHECK_ISO_FULL_DATE_GLOB


# ---- UTILS ---- #
def youtube_video_id_to_url(column: str, concat: str) -> str:
    return f"'https://www.youtube.com/watch?v=' {concat} {column}"


# ---- GENIUS TABLES + EXTENDED METADATA ---- #

# Genius Artist Info Table
GENIUS_ARTIST_INFO_TABLE_NAME: Final[TableName] = "genius_artist_info"
GENIUS_ARTIST_INFO_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {GENIUS_ARTIST_INFO_TABLE_NAME} (
    genius_id   INTEGER PRIMARY KEY
                    CHECK (genius_id > 0),
    name        TEXT NOT NULL
                    CHECK (name <> ''),
    genius_url  TEXT NOT NULL
                    CHECK (genius_url <> ''),
    image_url   TEXT
                    CHECK (image_url IS NULL OR image_url <> '')
) STRICT;
"""
GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("genius_id",)
GENIUS_ARTIST_INFO_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {}
GENIUS_ARTIST_INFO_TABLE_META: Final[TableMeta] = {
    "genius_id": FieldMeta(py_type=int, nullable=False),
    "name": FieldMeta(py_type=str, nullable=False),
    "genius_url": FieldMeta(py_type=str, nullable=False),
    "image_url": FieldMeta(py_type=str, nullable=True),
}

# Genius Album Info Table
GENIUS_ALBUM_INFO_TABLE_NAME: Final[TableName] = "genius_album_info"
GENIUS_ALBUM_INFO_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {GENIUS_ALBUM_INFO_TABLE_NAME} (
    genius_id                 INTEGER PRIMARY KEY
                                  CHECK (genius_id > 0),
    title                     TEXT NOT NULL
                                  CHECK (title <> ''),
    genius_url                TEXT NOT NULL
                                  CHECK (genius_url <> ''),
    primary_artist_genius_id  INTEGER NOT NULL,
    release_date              TEXT NOT NULL
                                  CHECK ({CHECK_ISO_FULL_DATE_GLOB(col="release_date")}),
    image_url                 TEXT
                                  CHECK (image_url IS NULL OR image_url <> ''),

    FOREIGN KEY (primary_artist_genius_id)
        REFERENCES {GENIUS_ARTIST_INFO_TABLE_NAME}({GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT
) STRICT;
"""
GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("genius_id",)
GENIUS_ALBUM_INFO_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_ARTIST_INFO_TABLE_NAME: {
        GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]: "primary_artist_genius_id",
    },
}
GENIUS_ALBUM_INFO_TABLE_META: Final[TableMeta] = {
    "genius_id": FieldMeta(py_type=int, nullable=False),
    "title": FieldMeta(py_type=str, nullable=False),
    "genius_url": FieldMeta(py_type=str, nullable=False),
    "primary_artist_genius_id": FieldMeta(py_type=int, nullable=False),
    "release_date": FieldMeta(py_type=str, nullable=False),
    "image_url": FieldMeta(py_type=str, nullable=True),
}

# Genius Song Info Table
GENIUS_SONG_INFO_TABLE_NAME: Final[TableName] = "genius_song_info"
GENIUS_SONG_INFO_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {GENIUS_SONG_INFO_TABLE_NAME} (
    genius_id                INTEGER PRIMARY KEY
                                 CHECK (genius_id > 0),
    title                    TEXT NOT NULL
                                 CHECK (title <> ''),
    genius_url               TEXT NOT NULL
                                 CHECK (genius_url <> ''),
    primary_artist_genius_id INTEGER NOT NULL,
    album_genius_id          INTEGER NOT NULL,
    release_date             TEXT NOT NULL
                                 CHECK ({CHECK_ISO_FULL_DATE_GLOB(col="release_date")}),
    image_url                TEXT
                                 CHECK (image_url IS NULL OR image_url <> ''),
    apple_music_id           TEXT
                                 CHECK (
                                     apple_music_id IS NULL 
                                     OR (length(apple_music_id) > 0 AND apple_music_id GLOB '[0-9]*')
                                 ),
    youtube_video_id         TEXT
                                 CHECK (
                                     youtube_video_id IS NULL
                                     OR (length(youtube_video_id) = 11 AND {CHECK_BASE64_URL_SAFE_GLOB(col="youtube_video_id")})
                                 ),
    language                 TEXT
                                 CHECK (language IS NULL OR language GLOB '[a-z][a-z]'),
    youtube_url              TEXT GENERATED ALWAYS AS (
                                CASE
                                    WHEN youtube_video_id IS NOT NULL THEN {youtube_video_id_to_url(column="youtube_video_id", concat=CONCAT)}
                                    ELSE NULL
                                END
                             ) VIRTUAL,

    FOREIGN KEY (primary_artist_genius_id)
        REFERENCES {GENIUS_ARTIST_INFO_TABLE_NAME}({GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT,

    FOREIGN KEY (album_genius_id)
        REFERENCES {GENIUS_ALBUM_INFO_TABLE_NAME}({GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT
) STRICT;
"""
GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = ("genius_id",)
GENIUS_SONG_INFO_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_ARTIST_INFO_TABLE_NAME: {
        GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]: "primary_artist_genius_id",
    },
    GENIUS_ALBUM_INFO_TABLE_NAME: {
        GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS[0]: "album_genius_id",
    },
}
GENIUS_SONG_INFO_TABLE_META: Final[TableMeta] = {
    "genius_id": FieldMeta(py_type=int, nullable=False),
    "title": FieldMeta(py_type=str, nullable=False),
    "genius_url": FieldMeta(py_type=str, nullable=False),
    "primary_artist_genius_id": FieldMeta(py_type=int, nullable=False),
    "album_genius_id": FieldMeta(py_type=int, nullable=False),
    "release_date": FieldMeta(py_type=str, nullable=False),
    "image_url": FieldMeta(py_type=str, nullable=True),
    "apple_music_id": FieldMeta(py_type=str, nullable=True),
    "youtube_video_id": FieldMeta(py_type=str, nullable=True),
    "language": FieldMeta(py_type=str, nullable=True),
}

# Genius Discography Entry Table
GENIUS_DISCOGRAPHY_TABLE_NAME: Final[TableName] = "genius_discography"
GENIUS_DISCOGRAPHY_TABLE: Final[CreateStatement] = f"""
CREATE TABLE IF NOT EXISTS {GENIUS_DISCOGRAPHY_TABLE_NAME} (
    artist_genius_id INTEGER NOT NULL,
    song_genius_id   INTEGER NOT NULL,

    PRIMARY KEY (artist_genius_id, song_genius_id),

    FOREIGN KEY (artist_genius_id)
        REFERENCES {GENIUS_ARTIST_INFO_TABLE_NAME}({GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE RESTRICT,

    FOREIGN KEY (song_genius_id)
        REFERENCES {GENIUS_SONG_INFO_TABLE_NAME}({GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS[0]})
        ON DELETE CASCADE
) STRICT;
"""
GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS: Final[PrimaryKeyNames] = (
    "artist_genius_id",
    "song_genius_id",
)
GENIUS_DISCOGRAPHY_TABLE_FOREIGN_KEYS: Final[ForeignKeyMapping] = {
    GENIUS_ARTIST_INFO_TABLE_NAME: {
        GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS[0]: "artist_genius_id",
    },
    GENIUS_SONG_INFO_TABLE_NAME: {
        GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS[0]: "song_genius_id",
    },
}
GENIUS_DISCOGRAPHY_TABLE_META: Final[TableMeta] = {
    "artist_genius_id": FieldMeta(py_type=int, nullable=False),
    "song_genius_id": FieldMeta(py_type=int, nullable=False),
}

# All Genius Tables Creation Statements in Order of Dependencies
TABLES: Final[list[CreateStatement]] = [
    GENIUS_ARTIST_INFO_TABLE,
    GENIUS_ALBUM_INFO_TABLE,
    GENIUS_SONG_INFO_TABLE,
    GENIUS_DISCOGRAPHY_TABLE,
]
