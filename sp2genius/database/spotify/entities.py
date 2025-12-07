import sqlite3

from ..core import BaseEntity
from .tables import (
    ALBUM_IMAGES_TABLE_COL_META,
    ALBUM_IMAGES_TABLE_PRIMARY_KEYS,
    ALBUMS_TABLE_COL_META,
    ALBUMS_TABLE_PRIMARY_KEYS,
    ARTIST_IMAGES_TABLE_COL_META,
    ARTIST_IMAGES_TABLE_PRIMARY_KEYS,
    ARTISTS_TABLE_COL_META,
    ARTISTS_TABLE_PRIMARY_KEYS,
    DISCOGRAPHY_TABLE_COL_META,
    DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    SONGS_TABLE_COL_META,
    SONGS_TABLE_PRIMARY_KEYS,
)

CONCAT = "||"  # SQLite string concatenation operator
FOREIGN_KEYS = True
YEAR_GLOB = r"[0-9][0-9][0-9][0-9]"
MONTH_GLOB = r"[0-9][0-9]"
DAY_GLOB = r"[0-9][0-9]"

ISO_YEAR = f"{YEAR_GLOB}"
ISO_YEAR_MONTH = f"{YEAR_GLOB}-{MONTH_GLOB}"
ISO_FULL_DATE = f"{YEAR_GLOB}-{MONTH_GLOB}-{DAY_GLOB}"


class ArtistImage(BaseEntity):
    FIELD_META = ARTIST_IMAGES_TABLE_COL_META.copy()
    PRIMARY_KEYS = ARTIST_IMAGES_TABLE_PRIMARY_KEYS
    TABLE_NAME = "artist_images"


class AlbumImage(BaseEntity):
    FIELD_META = ALBUM_IMAGES_TABLE_COL_META.copy()
    PRIMARY_KEYS = ALBUM_IMAGES_TABLE_PRIMARY_KEYS
    TABLE_NAME = "album_images"


class Album(BaseEntity):
    FIELD_META = ALBUMS_TABLE_COL_META.copy()
    PRIMARY_KEYS = ALBUMS_TABLE_PRIMARY_KEYS
    TABLE_NAME = "albums"

    def register_image(
        self,
        cur: sqlite3.Cursor,
        image: AlbumImage,
        simulate: bool = False,
    ) -> None:
        data = self.curr_state_dict()
        if data.album_id != image.album_id:  # type: ignore
            raise ValueError("An image attached to an album must reference its album_id")
        image.upsert_to_db(cur=cur, simulate=simulate)


class Song(BaseEntity):
    FIELD_META = SONGS_TABLE_COL_META.copy()
    PRIMARY_KEYS = SONGS_TABLE_PRIMARY_KEYS
    TABLE_NAME = "songs"


class DiscographyEntry(BaseEntity):
    FIELD_META = DISCOGRAPHY_TABLE_COL_META.copy()
    PRIMARY_KEYS = DISCOGRAPHY_TABLE_PRIMARY_KEYS
    TABLE_NAME = "discography"

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        super().insert_to_db(cur=cur, simulate=simulate, on_conflict=True)

    def update_fields_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        raise NotImplementedError(
            "DiscographyEntry.update_fields_db is not implemented."
            "Use insert_to_db instead, as discography entries are immutable."
        )

    def upsert_to_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> None:
        raise NotImplementedError(
            "DiscographyEntry.upsert_to_db is not implemented."
            "Use insert_to_db instead, as discography entries are immutable."
        )


class Artist(BaseEntity):
    FIELD_META = ARTISTS_TABLE_COL_META.copy()
    PRIMARY_KEYS = ARTISTS_TABLE_PRIMARY_KEYS
    TABLE_NAME = "artists"

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: Song,
        simulate: bool = False,
    ) -> None:
        data = self.curr_state_dict()
        entry = DiscographyEntry(
            data={
                "track_id": song.track_id,  # type: ignore
                "artist_id": data["artist_id"],
            }
        )
        entry.insert_to_db(cur=cur, simulate=simulate)

    def register_image(
        self,
        cur: sqlite3.Cursor,
        image: ArtistImage,
        simulate: bool = False,
    ) -> None:
        data = self.curr_state_dict()
        if data.artist_id != image.artist_id:  # type: ignore
            raise ValueError("An image attached to an artist must reference its artist_id")
        image.upsert_to_db(cur=cur, simulate=simulate)
