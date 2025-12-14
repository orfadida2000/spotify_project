import sqlite3

from sp2genius.utils import err_msg

from ..core import UNSET, BaseEntity, BasicFieldValue
from .tables import (
    GENIUS_ALBUM_INFO_TABLE_COL_META,
    GENIUS_ALBUM_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_ALBUM_INFO_TABLE_NAME,
    GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_ARTIST_INFO_TABLE_COL_META,
    GENIUS_ARTIST_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_ARTIST_INFO_TABLE_NAME,
    GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_DISCOGRAPHY_TABLE_COL_META,
    GENIUS_DISCOGRAPHY_TABLE_FOREIGN_KEYS,
    GENIUS_DISCOGRAPHY_TABLE_NAME,
    GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    GENIUS_SONG_INFO_TABLE_COL_META,
    GENIUS_SONG_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_SONG_INFO_TABLE_NAME,
    GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS,
)


class GeniusAlbumInfo(BaseEntity):
    FIELD_META = GENIUS_ALBUM_INFO_TABLE_COL_META
    PRIMARY_KEYS = GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_ALBUM_INFO_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_ALBUM_INFO_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        album_genius_id: int | BasicFieldValue = UNSET,
        album_title: str | BasicFieldValue = UNSET,
        album_genius_url: str | BasicFieldValue = UNSET,
        primary_artist_genius_id: int | BasicFieldValue = UNSET,
        release_date: str | BasicFieldValue = UNSET,
        album_image_url: str | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "genius_id": album_genius_id,
            "title": album_title,
            "genius_url": album_genius_url,
            "primary_artist_genius_id": primary_artist_genius_id,
            "release_date": release_date,
            "image_url": album_image_url,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)

    def get_genius_url(self) -> str | BasicFieldValue:
        return getattr(self, "genius_url", UNSET)

    def get_primary_artist_id(self) -> int | BasicFieldValue:
        return getattr(self, "primary_artist_genius_id", UNSET)


class GeniusSongInfo(BaseEntity):
    FIELD_META = GENIUS_SONG_INFO_TABLE_COL_META
    PRIMARY_KEYS = GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_SONG_INFO_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_SONG_INFO_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        song_genius_id: int | BasicFieldValue = UNSET,
        song_title: str | BasicFieldValue = UNSET,
        song_genius_url: str | BasicFieldValue = UNSET,
        primary_artist_genius_id: int | BasicFieldValue = UNSET,
        album_genius_id: int | BasicFieldValue = UNSET,
        release_date: str | BasicFieldValue = UNSET,
        song_image_url: str | BasicFieldValue = UNSET,
        apple_music_id: str | BasicFieldValue = UNSET,
        youtube_video_id: str | BasicFieldValue = UNSET,
        language: str | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "genius_id": song_genius_id,
            "title": song_title,
            "genius_url": song_genius_url,
            "primary_artist_genius_id": primary_artist_genius_id,
            "album_genius_id": album_genius_id,
            "release_date": release_date,
            "image_url": song_image_url,
            "apple_music_id": apple_music_id,
            "youtube_video_id": youtube_video_id,
            "language": language,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)

    def get_genius_url(self) -> str | BasicFieldValue:
        return getattr(self, "genius_url", UNSET)

    def get_primary_artist_id(self) -> int | BasicFieldValue:
        return getattr(self, "primary_artist_genius_id", UNSET)

    def get_album_id(self) -> int | BasicFieldValue:
        return getattr(self, "album_genius_id", UNSET)


class GeniusDiscographyEntry(BaseEntity):
    FIELD_META = GENIUS_DISCOGRAPHY_TABLE_COL_META
    PRIMARY_KEYS = GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_DISCOGRAPHY_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_DISCOGRAPHY_TABLE_NAME

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        super().insert_to_db(cur=cur, simulate=simulate, on_conflict=True)

    def update_fields_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        raise NotImplementedError(
            err_msg(
                "this method is not implemented. "
                "Use insert_to_db instead, as discography entries are immutable."
            )
        )

    def upsert_to_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> None:
        raise NotImplementedError(
            err_msg(
                "this method is not implemented. "
                "Use insert_to_db instead, as discography entries are immutable."
            )
        )

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_genius_id: int | BasicFieldValue = UNSET,
        song_genius_id: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "artist_genius_id": artist_genius_id,
            "song_genius_id": song_genius_id,
        }
        return cls._filter_fields(fields)

    def get_artist_id(self) -> int | BasicFieldValue:
        return getattr(self, "artist_genius_id", UNSET)

    def get_song_id(self) -> int | BasicFieldValue:
        return getattr(self, "song_genius_id", UNSET)


class GeniusArtistInfo(BaseEntity):
    FIELD_META = GENIUS_ARTIST_INFO_TABLE_COL_META
    PRIMARY_KEYS = GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_ARTIST_INFO_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_ARTIST_INFO_TABLE_NAME

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: GeniusSongInfo,
        simulate: bool = False,
    ) -> None:
        entry = GeniusDiscographyEntry(
            data=GeniusDiscographyEntry.make_init_data(
                artist_genius_id=self.get_id(),
                song_genius_id=song.get_id(),
            )
        )
        entry.insert_to_db(cur=cur, simulate=simulate)

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_genius_id: int | BasicFieldValue = UNSET,
        artist_name: str | BasicFieldValue = UNSET,
        artist_genius_url: str | BasicFieldValue = UNSET,
        artist_image_url: str | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "genius_id": artist_genius_id,
            "name": artist_name,
            "genius_url": artist_genius_url,
            "image_url": artist_image_url,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)

    def get_genius_url(self) -> str | BasicFieldValue:
        return getattr(self, "genius_url", UNSET)
