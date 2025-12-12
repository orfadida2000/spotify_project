from ..core import CHECK_BASE64_URL_SAFE_GLOB, CHECK_ISO_FULL_DATE_GLOB, CONCAT


def youtube_video_id_to_url(column: str, concat: str) -> str:
    return f"'https://www.youtube.com/watch?v=' {concat} {column}"


GENIUS_ARTIST_INFO_TABLE = """
CREATE TABLE IF NOT EXISTS genius_artist_info (
    genius_id   INTEGER PRIMARY KEY
                    CHECK (genius_id > 0),
    name        TEXT NOT NULL
                    CHECK (name <> ''),
    genius_url  TEXT NOT NULL
                    CHECK (genius_url <> ''),
    image_url   TEXT
                    CHECK (image_url IS NULL OR image_url <> '')
);
"""
GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS = ("genius_id",)
GENIUS_ARTIST_INFO_TABLE_COL_META = {
    "genius_id": (True, int),
    "name": (True, str),
    "genius_url": (True, str),
    "image_url": (False, str),
}

GENIUS_ALBUM_INFO_TABLE = f"""
CREATE TABLE IF NOT EXISTS genius_album_info (
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
        REFERENCES genius_artist_info(genius_id)
        ON DELETE RESTRICT
);
"""
GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS = ("genius_id",)
GENIUS_ALBUM_INFO_TABLE_COL_META = {
    "genius_id": (True, int),
    "title": (True, str),
    "genius_url": (True, str),
    "primary_artist_genius_id": (True, int),
    "release_date": (True, str),
    "image_url": (False, str),
}

GENIUS_SONG_INFO_TABLE = f"""
CREATE TABLE IF NOT EXISTS genius_song_info (
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
        REFERENCES genius_artist_info(genius_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (album_genius_id)
        REFERENCES genius_album_info(genius_id)
        ON DELETE RESTRICT
);
"""
GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS = ("genius_id",)
GENIUS_SONG_INFO_TABLE_COL_META = {
    "genius_id": (True, int),
    "title": (True, str),
    "genius_url": (True, str),
    "primary_artist_genius_id": (True, int),
    "album_genius_id": (True, int),
    "release_date": (True, str),
    "image_url": (False, str),
    "apple_music_id": (False, str),
    "youtube_video_id": (False, str),
    "language": (False, str),
}

GENIUS_DISCOGRAPHY_TABLE = """
CREATE TABLE IF NOT EXISTS genius_discography (
    artist_genius_id INTEGER NOT NULL,
    song_genius_id   INTEGER NOT NULL,

    PRIMARY KEY (artist_genius_id, song_genius_id),

    FOREIGN KEY (artist_genius_id)
        REFERENCES genius_artist_info(genius_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (song_genius_id)
        REFERENCES genius_song_info(genius_id)
        ON DELETE CASCADE
);
"""
GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS = ("artist_genius_id", "song_genius_id")
GENIUS_DISCOGRAPHY_TABLE_COL_META = {
    "artist_genius_id": (True, int),
    "song_genius_id": (True, int),
}


TABLES = [
    GENIUS_ARTIST_INFO_TABLE,
    GENIUS_ALBUM_INFO_TABLE,
    GENIUS_SONG_INFO_TABLE,
    GENIUS_DISCOGRAPHY_TABLE,
]
