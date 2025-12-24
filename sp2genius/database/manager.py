import sqlite3
from contextlib import contextmanager
from pathlib import Path

import genius.manager as genius_manager
import spotify.manager as spotify_manager

from sp2genius.lyrics import insert
from sp2genius.utils import err_msg
from sp2genius.utils.path import get_absolute_path

from . import DB_PATH
from .entities import (
    Album,
    AlbumImage,
    Artist,
    ArtistImage,
    DiscographyEntry,
    GeniusAlbumInfo,
    GeniusArtistInfo,
    GeniusDiscographyEntry,
    GeniusSongInfo,
    Song,
)
from .schema import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_META_TABLE,
    SQL_CREATE_STATEMENTS,
    SQL_PRAGMA_STATEMENT,
    VALID_SCHEMA_ID,
)


class DbManager:
    """
    Manages the SQLite database connection and ensures the schema is initialized.

    Class Attributes:
        DEFAULT_DB_PATH (Path): The default path to the database file.

    Instance Attributes:
        db_path (Path): The path to the database file.
        conn (sqlite3.Connection | None): The active database connection.
        initialized (bool): Indicates whether the database schema has been initialized.
    """

    DEFAULT_DB_PATH: Path = DB_PATH
    DEFAULT_ROW_FACTORY = sqlite3.Row

    def __init__(self, db_path: str | Path | None = None):
        self.db_path: Path = self._resolve_db_path(db_path)
        self.conn: sqlite3.Connection | None = None
        self.initialized: bool = False

    @contextmanager
    def transaction(self):
        if self.conn is None:
            raise RuntimeError(err_msg("Database connection is not open."))
        try:
            yield  # <-- the with-block runs here
        except Exception:
            self.conn.rollback()  # <-- runs only if with-block raised
            raise
        else:
            self.conn.commit()  # <-- runs only if with-block did NOT raise

    @classmethod
    def _resolve_db_path(cls, db_path: str | Path | None) -> Path:
        if db_path is None:
            db_path = cls.DEFAULT_DB_PATH

        p = get_absolute_path(db_path)
        if p is None:
            raise ValueError(err_msg("The provided db_path is empty or invalid."))

        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def open(self) -> None:
        if self.conn is not None:
            return

        conn = sqlite3.connect(database=self.db_path, autocommit=False)
        conn.row_factory = self.DEFAULT_ROW_FACTORY

        try:
            conn.execute(SQL_PRAGMA_STATEMENT)

            if not self.initialized:
                self._ensure_initialized(conn)
                self.initialized = True
        except Exception:
            conn.close()
            raise
        else:
            self.conn = conn

    def close(self) -> None:
        if self.conn is None:
            return
        self.conn.close()
        self.conn = None

    @staticmethod
    def _ensure_initialized(conn: sqlite3.Connection) -> None:
        try:
            # Ensure schema_meta exists
            conn.execute(SCHEMA_META_TABLE)

            # Check current DB version
            row = conn.execute(
                "SELECT version FROM schema_meta WHERE id = :id",
                {"id": VALID_SCHEMA_ID},
            ).fetchone()

            if row is None:
                # Brand-new DB: create all tables and set version
                conn.executescript(SQL_CREATE_STATEMENTS)
                conn.execute(
                    "INSERT INTO schema_meta (id, version) VALUES (:id, :version)",
                    {"id": VALID_SCHEMA_ID, "version": CURRENT_SCHEMA_VERSION},
                )
                conn.commit()
                return

            db_version = row[0]
            if db_version < CURRENT_SCHEMA_VERSION:
                raise NotImplementedError(
                    err_msg(
                        f"Database schema version {db_version} is outdated. "
                        f"Current version is {CURRENT_SCHEMA_VERSION}. "
                        "Automatic migrations are not yet implemented."
                    )
                )
            if db_version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    err_msg(
                        f"Database schema version {db_version} is newer than the current "
                        f"supported version {CURRENT_SCHEMA_VERSION}. "
                        "Please update the application."
                    )
                )
        except Exception:
            conn.rollback()
            raise

    def insert_song_spotify_data(
        self,
        *,
        song: Song,
        primary_artist: tuple[Artist, list[ArtistImage]],
        album: tuple[Album, list[AlbumImage]],
        featured_artists: list[tuple[Artist, list[ArtistImage]]],
    ) -> None:
        with self.transaction():
            spotify_manager.insert_spotify_song(
                self.conn,  # type: ignore
                song=song,
                primary_artist=primary_artist,
                album=album,
                featured_artists=featured_artists,
            )

    def insert_song_genius_data(
        self,
        *,
        song: GeniusSongInfo,
        primary_artist: GeniusArtistInfo,
        album: GeniusAlbumInfo,
        featured_artists: list[GeniusArtistInfo],
    ) -> None:
        with self.transaction():
            genius_manager.insert_genius_song_info(
                self.conn,  # type: ignore
                song=song,
                primary_artist=primary_artist,
                album=album,
                featured_artists=featured_artists,
            )

    def insert_song(
        self,
        *,
        spotify_song: Song | None = None,
        spotify_primary_artist: tuple[Artist, list[ArtistImage]] | None = None,
        spotify_album: tuple[Album, list[AlbumImage]] | None = None,
        spotify_featured_artists: list[tuple[Artist, list[ArtistImage]]] | None = None,
        genius_song: GeniusSongInfo | None = None,
        genius_primary_artist: GeniusArtistInfo | None = None,
        genius_album: GeniusAlbumInfo | None = None,
        genius_featured_artists: list[GeniusArtistInfo] | None = None,
    ):
        spotify_data = {
            "song": spotify_song,
            "primary_artist": spotify_primary_artist,
            "album": spotify_album,
            "featured_artists": spotify_featured_artists,
        }
        genius_data = {
            "song": genius_song,
            "primary_artist": genius_primary_artist,
            "album": genius_album,
            "featured_artists": genius_featured_artists,
        }
        assert all(v is not None for v in spotify_data.values()) or all(
            v is None for v in spotify_data.values()
        ), err_msg("Spotify data must be either fully provided or fully omitted.")
        insert_spotify_data: bool = spotify_data["song"] is not None

        assert all(v is not None for v in genius_data.values()) or all(
            v is None for v in genius_data.values()
        ), err_msg("Genius data must be either fully provided or fully omitted.")
        insert_genius_data: bool = genius_data["song"] is not None

        if not insert_spotify_data and not insert_genius_data:
            raise ValueError(err_msg("At least one of Spotify or Genius data must be provided."))
        elif not insert_spotify_data and insert_genius_data:
            self.insert_song_genius_data(**genius_data)
        elif insert_spotify_data and not insert_genius_data:
            self.insert_song_spotify_data(**spotify_data)
        else:
            with self.transaction():
                genius_manager.insert_genius_song_info(
                    self.conn,  # type: ignore
                    **genius_data,
                )
                song_genius_id = genius_data["song"].get_id()
                album_genius_id = genius_data["album"].get_id()
