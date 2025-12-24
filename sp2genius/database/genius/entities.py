import sqlite3

from ..core.base import BinaryAssociationEntity, SinglePkEntity
from ..core.constants import UNSET
from ..core.typing import BasicFieldValue
from .tables import (
    GENIUS_ALBUM_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_ALBUM_INFO_TABLE_META,
    GENIUS_ALBUM_INFO_TABLE_NAME,
    GENIUS_ALBUM_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_ARTIST_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_ARTIST_INFO_TABLE_META,
    GENIUS_ARTIST_INFO_TABLE_NAME,
    GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS,
    GENIUS_DISCOGRAPHY_TABLE_FOREIGN_KEYS,
    GENIUS_DISCOGRAPHY_TABLE_META,
    GENIUS_DISCOGRAPHY_TABLE_NAME,
    GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    GENIUS_SONG_INFO_TABLE_FOREIGN_KEYS,
    GENIUS_SONG_INFO_TABLE_META,
    GENIUS_SONG_INFO_TABLE_NAME,
    GENIUS_SONG_INFO_TABLE_PRIMARY_KEYS,
)


class GeniusEntity(SinglePkEntity):
    @classmethod
    def get_id_col_name(cls) -> str:
        return cls.get_pk_name()

    def get_id(self) -> int:
        return self.get_pk_value()

    def set_id(self, new_id: int) -> None:
        self.set_pk_value(new_id)

    @classmethod
    def get_genius_url_col_name(cls) -> str:
        return "genius_url"

    def get_genius_url(self) -> str:
        genius_url_col_name = self.get_genius_url_col_name()
        return self.get_field_value(genius_url_col_name)

    def set_genius_url(self, new_url: str) -> None:
        genius_url_col_name = self.get_genius_url_col_name()
        self.set_field_value(genius_url_col_name, new_url)

    @classmethod
    def get_image_url_col_name(cls) -> str:
        return "image_url"

    def get_image_url(self) -> str | BasicFieldValue:
        image_url_col_name = self.get_image_url_col_name()
        return self.get_field_value(image_url_col_name)

    def set_image_url(self, new_url: str | BasicFieldValue) -> None:
        image_url_col_name = self.get_image_url_col_name()
        self.set_field_value(image_url_col_name, new_url)


class GeniusAlbumInfo(GeniusEntity):
    TABLE_META = GENIUS_ALBUM_INFO_TABLE_META
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
            cls.get_id_col_name(): album_genius_id,
            cls.get_title_col_name(): album_title,
            cls.get_genius_url_col_name(): album_genius_url,
            cls.get_primary_artist_id_col_name(): primary_artist_genius_id,
            "release_date": release_date,
            cls.get_image_url_col_name(): album_image_url,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_primary_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(GeniusArtistInfo)

    def get_primary_artist_id(self) -> int:
        return self.get_fk_value_ref_single_pk_entity(GeniusArtistInfo)

    def set_primary_artist_id(self, new_id: int) -> None:
        self.set_fk_value_ref_single_pk_entity(GeniusArtistInfo, new_id)

    @classmethod
    def get_title_col_name(cls) -> str:
        return "title"

    def get_title(self) -> str:
        title_col_name = self.get_title_col_name()
        return self.get_field_value(title_col_name)

    def set_title(self, new_title: str) -> None:
        title_col_name = self.get_title_col_name()
        self.set_field_value(title_col_name, new_title)


class GeniusSongInfo(GeniusEntity):
    TABLE_META = GENIUS_SONG_INFO_TABLE_META
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
            cls.get_id_col_name(): song_genius_id,
            cls.get_title_col_name(): song_title,
            cls.get_genius_url_col_name(): song_genius_url,
            cls.get_primary_artist_id_col_name(): primary_artist_genius_id,
            cls.get_album_id_col_name(): album_genius_id,
            "release_date": release_date,
            cls.get_image_url_col_name(): song_image_url,
            "apple_music_id": apple_music_id,
            "youtube_video_id": youtube_video_id,
            "language": language,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_primary_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(GeniusArtistInfo)

    def get_primary_artist_id(self) -> int:
        return self.get_fk_value_ref_single_pk_entity(GeniusArtistInfo)

    def set_primary_artist_id(self, new_id: int) -> None:
        self.set_fk_value_ref_single_pk_entity(GeniusArtistInfo, new_id)

    @classmethod
    def get_album_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(GeniusAlbumInfo)

    def get_album_id(self) -> int:
        return self.get_fk_value_ref_single_pk_entity(GeniusAlbumInfo)

    def set_album_id(self, new_id: int) -> None:
        self.set_fk_value_ref_single_pk_entity(GeniusAlbumInfo, new_id)

    @classmethod
    def get_title_col_name(cls) -> str:
        return "title"

    def get_title(self) -> str:
        title_col_name = self.get_title_col_name()
        return self.get_field_value(title_col_name)

    def set_title(self, new_title: str) -> None:
        title_col_name = self.get_title_col_name()
        self.set_field_value(title_col_name, new_title)


class GeniusDiscographyEntry(BinaryAssociationEntity):
    TABLE_META = GENIUS_DISCOGRAPHY_TABLE_META
    PRIMARY_KEYS = GENIUS_DISCOGRAPHY_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_DISCOGRAPHY_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_DISCOGRAPHY_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_genius_id: int | BasicFieldValue = UNSET,
        song_genius_id: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            cls.get_artist_id_col_name(): artist_genius_id,
            cls.get_song_id_col_name(): song_genius_id,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(GeniusArtistInfo)

    def get_artist_id(self) -> int:
        return self.get_fk_value_ref_single_pk_entity(GeniusArtistInfo)

    def set_artist_id(self, new_id: int) -> None:
        self.set_fk_value_ref_single_pk_entity(GeniusArtistInfo, new_id)

    @classmethod
    def get_song_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(GeniusSongInfo)

    def get_song_id(self) -> int:
        return self.get_fk_value_ref_single_pk_entity(GeniusSongInfo)

    def set_song_id(self, new_id: int) -> None:
        self.set_fk_value_ref_single_pk_entity(GeniusSongInfo, new_id)


class GeniusArtistInfo(GeniusEntity):
    TABLE_META = GENIUS_ARTIST_INFO_TABLE_META
    PRIMARY_KEYS = GENIUS_ARTIST_INFO_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = GENIUS_ARTIST_INFO_TABLE_FOREIGN_KEYS
    TABLE_NAME = GENIUS_ARTIST_INFO_TABLE_NAME

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: GeniusSongInfo,
        simulate: bool = False,
    ) -> None:
        entry_data = {}
        entry_data[GeniusDiscographyEntry.get_artist_id_col_name()] = self.get_id()
        entry_data[GeniusDiscographyEntry.get_song_id_col_name()] = song.get_id()
        entry = GeniusDiscographyEntry(data=entry_data)
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
            cls.get_id_col_name(): artist_genius_id,
            cls.get_name_col_name(): artist_name,
            cls.get_genius_url_col_name(): artist_genius_url,
            cls.get_image_url_col_name(): artist_image_url,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_name_col_name(cls) -> str:
        return "name"

    def get_name(self) -> str:
        name_col_name = self.get_name_col_name()
        return self.get_field_value(name_col_name)

    def set_name(self, new_name: str) -> None:
        name_col_name = self.get_name_col_name()
        self.set_field_value(name_col_name, new_name)
