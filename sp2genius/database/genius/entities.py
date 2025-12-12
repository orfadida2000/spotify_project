import sqlite3

from ..core import UNSET, BaseEntity, BasicFieldValue
from .tables import (
    GENIUS_ALBUM_INFO_TABLE_COL_META,
    GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_ARTIST_INFO_TABLE_COL_META,
    GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_DISCOGRAPHY_TABLE_COL_META,
    GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    GENIUS_SONG_INFO_TABLE_COL_META,
    GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS,
)


class GeniusAlbumInfo(BaseEntity):
    FIELD_META = GENIUS_ALBUM_INFO_TABLE_COL_META.copy()
    PRIMARY_KEYS = GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS
    TABLE_NAME = "genius_album_info"

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


class GeniusSongInfo(BaseEntity):
    FIELD_META = GENIUS_SONG_INFO_TABLE_COL_META.copy()
    PRIMARY_KEYS = GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS
    TABLE_NAME = "genius_song_info"

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


class GeniusDiscographyEntry(BaseEntity):
    FIELD_META = GENIUS_DISCOGRAPHY_TABLE_COL_META.copy()
    PRIMARY_KEYS = GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS
    TABLE_NAME = "genius_discography"

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        super().insert_to_db(cur=cur, simulate=simulate, on_conflict=True)

    def update_fields_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        raise NotImplementedError(
            f"{self.__class__.__name__}.update_fields_db is not implemented."
            "Use insert_to_db instead, as discography entries are immutable."
        )

    def upsert_to_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__}.upsert_to_db is not implemented."
            "Use insert_to_db instead, as discography entries are immutable."
        )


class GeniusArtistInfo(BaseEntity):
    FIELD_META = GENIUS_ARTIST_INFO_TABLE_COL_META.copy()
    PRIMARY_KEYS = GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS
    TABLE_NAME = "genius_artist_info"

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: GeniusSongInfo,
        simulate: bool = False,
    ) -> None:
        data = self.curr_state_dict()
        entry = GeniusDiscographyEntry(
            data={
                "artist_genius_id": data["genius_id"],
                "song_genius_id": song.genius_id,  # type: ignore
            }
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
