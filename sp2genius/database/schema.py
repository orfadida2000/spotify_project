def _track_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/track/' {concat} {column}"


def _artist_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/artist/' {concat} {column}"


def _album_id_to_url(column: str, concat: str) -> str:
    return f"'https://open.spotify.com/album/' {concat} {column}"


def id_to_url(column: str, concat: str, entity: str) -> str:
    if entity == "track":
        return _track_id_to_url(column, concat)
    elif entity == "artist":
        return _artist_id_to_url(column, concat)
    elif entity == "album":
        return _album_id_to_url(column, concat)
    else:
        raise ValueError(f"Unknown entity type: {entity}")


CONCAT = "||"  # SQLite string concatenation operator
CHECK_ID_GLOB = "{id} GLOB '[A-Za-z0-9]*' AND length({id}) = 22"

ARTISTS_TABLE = f"""
CREATE TABLE IF NOT EXISTS artists (
    artist_id       TEXT PRIMARY KEY
                    CHECK ({CHECK_ID_GLOB.format(id="artist_id")}),
    name            TEXT NOT NULL
                    CHECK (length(name) > 0),
    total_followers INTEGER
                    CHECK (total_followers >= 0),
    genres          TEXT,
    popularity      INTEGER
                    CHECK (popularity >= 0 AND popularity <= 100),
    spotify_url     TEXT GENERATED ALWAYS AS (
                        {id_to_url("artist_id", CONCAT, "artist")}
                    ) VIRTUAL
);
"""
ARTISTS_TABLE_PRIMARY_KEYS = ("artist_id",)
ARTISTS_TABLE_COL_META = {
    "artist_id": True,
    "name": True,
    "total_followers": False,
    "genres": False,
    "popularity": False,
}

# --- Date format constants -----------------------------------------------------

YEAR_GLOB = r"[0-9][0-9][0-9][0-9]"
MONTH_GLOB = r"[0-9][0-9]"
DAY_GLOB = r"[0-9][0-9]"

ISO_YEAR = f"{YEAR_GLOB}"
ISO_YEAR_MONTH = f"{YEAR_GLOB}-{MONTH_GLOB}"
ISO_FULL_DATE = f"{YEAR_GLOB}-{MONTH_GLOB}-{DAY_GLOB}"

ALBUMS_TABLE = f"""
CREATE TABLE IF NOT EXISTS albums (
    album_id               TEXT PRIMARY KEY
                           CHECK ({CHECK_ID_GLOB.format(id="album_id")}),
    title                  TEXT NOT NULL
                           CHECK (length(title) > 0),
    primary_artist_id      TEXT NOT NULL,
    album_type             TEXT NOT NULL
                           CHECK (album_type IN ('album', 'single', 'compilation')),
    total_tracks           INTEGER NOT NULL
                           CHECK (total_tracks > 0),
    release_date           TEXT NOT NULL
                           CHECK (
                             (length(release_date) = 4  AND release_date GLOB '{ISO_YEAR}')
                             OR
                             (length(release_date) = 7  AND release_date GLOB '{ISO_YEAR_MONTH}')
                             OR
                             (length(release_date) = 10 AND release_date GLOB '{ISO_FULL_DATE}')
                           ),
    release_date_precision TEXT GENERATED ALWAYS AS (
                               CASE
                                   WHEN length(release_date) = 4  THEN 'year'
                                   WHEN length(release_date) = 7  THEN 'month'
                                   WHEN length(release_date) = 10 THEN 'day'
                               END
                           ) VIRTUAL,
    label                  TEXT
                           CHECK (length(label) > 0),
    popularity             INTEGER
                           CHECK (popularity >= 0 AND popularity <= 100),
    spotify_url            TEXT GENERATED ALWAYS AS (
                               {id_to_url("album_id", CONCAT, "album")}
                           ) VIRTUAL,
    FOREIGN KEY (primary_artist_id) REFERENCES artists (artist_id)
);
"""
ALBUMS_TABLE_PRIMARY_KEYS = ("album_id",)
ALBUMS_TABLE_COL_META = {
    "album_id": True,
    "title": True,
    "primary_artist_id": True,
    "album_type": True,
    "total_tracks": True,
    "release_date": True,
    "label": False,
    "popularity": False,
}

SONGS_TABLE = f"""
CREATE TABLE IF NOT EXISTS songs (
    track_id          TEXT PRIMARY KEY
                      CHECK ({CHECK_ID_GLOB.format(id="track_id")}),
    title             TEXT NOT NULL
                      CHECK (length(title) > 0),
    genius_url        TEXT,
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
                          {id_to_url("track_id", CONCAT, "track")}
                      ) VIRTUAL,
    FOREIGN KEY (primary_artist_id) REFERENCES artists (artist_id),
    FOREIGN KEY (album_id)          REFERENCES albums (album_id)
);
"""
SONGS_TABLE_PRIMARY_KEYS = ("track_id",)
SONGS_TABLE_COL_META = {
    "track_id": True,
    "title": True,
    "genius_url": False,
    "primary_artist_id": True,
    "album_id": True,
    "disc_number": True,
    "track_number": True,
    "duration_ms": True,
    "explicit": True,
    "popularity": True,
}

DISCOGRAPHY_TABLE = """
CREATE TABLE IF NOT EXISTS discography (
    artist_id TEXT NOT NULL,
    track_id  TEXT NOT NULL,
    PRIMARY KEY (artist_id, track_id),
    FOREIGN KEY (artist_id) REFERENCES artists (artist_id),
    FOREIGN KEY (track_id)  REFERENCES songs   (track_id)
);
"""
DISCOGRAPHY_TABLE_PRIMARY_KEYS = ("artist_id", "track_id")
DISCOGRAPHY_TABLE_COL_META = {
    "artist_id": True,
    "track_id": True,
}

ARTIST_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS artist_images (
    artist_id TEXT NOT NULL,
    url       TEXT NOT NULL
              CHECK (length(url) > 0),
    width     INTEGER
              CHECK (width > 0),
    height    INTEGER
              CHECK (height > 0),
    PRIMARY KEY (artist_id, url),
    FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
);
"""
ARTIST_IMAGES_TABLE_PRIMARY_KEYS = ("artist_id", "url")
ARTIST_IMAGES_TABLE_COL_META = {
    "artist_id": True,
    "url": True,
    "width": False,
    "height": False,
}

ALBUM_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS album_images (
    album_id  TEXT NOT NULL,
    url       TEXT NOT NULL
              CHECK (length(url) > 0),
    width     INTEGER
              CHECK (width > 0),
    height    INTEGER
              CHECK (height > 0),
    PRIMARY KEY (album_id, url),
    FOREIGN KEY (album_id) REFERENCES albums (album_id)
);
"""
ALBUM_IMAGES_TABLE_PRIMARY_KEYS = ("album_id", "url")
ALBUM_IMAGES_TABLE_COL_META = {
    "album_id": True,
    "url": True,
    "width": False,
    "height": False,
}


TABLES = [
    ARTISTS_TABLE,
    ALBUMS_TABLE,
    SONGS_TABLE,
    DISCOGRAPHY_TABLE,
    ARTIST_IMAGES_TABLE,
    ALBUM_IMAGES_TABLE,
]
FULL_SCHEMA = "\n".join(TABLES)
FOREIGN_KEYS = True
