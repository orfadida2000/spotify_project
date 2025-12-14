import sqlite3

from sp2genius.utils import err_msg

from ..core import UNSET, BaseEntity, BasicFieldValue
from .tables import (
    ALBUM_IMAGES_TABLE_COL_META,
    ALBUM_IMAGES_TABLE_FOREIGN_KEYS,
    ALBUM_IMAGES_TABLE_NAME,
    ALBUM_IMAGES_TABLE_PRIMARY_KEYS,
    ALBUMS_TABLE_COL_META,
    ALBUMS_TABLE_FOREIGN_KEYS,
    ALBUMS_TABLE_NAME,
    ALBUMS_TABLE_PRIMARY_KEYS,
    ARTIST_IMAGES_TABLE_COL_META,
    ARTIST_IMAGES_TABLE_FOREIGN_KEYS,
    ARTIST_IMAGES_TABLE_NAME,
    ARTIST_IMAGES_TABLE_PRIMARY_KEYS,
    ARTISTS_TABLE_COL_META,
    ARTISTS_TABLE_FOREIGN_KEYS,
    ARTISTS_TABLE_NAME,
    ARTISTS_TABLE_PRIMARY_KEYS,
    DISCOGRAPHY_TABLE_COL_META,
    DISCOGRAPHY_TABLE_FOREIGN_KEYS,
    DISCOGRAPHY_TABLE_NAME,
    DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    SONGS_TABLE_COL_META,
    SONGS_TABLE_FOREIGN_KEYS,
    SONGS_TABLE_NAME,
    SONGS_TABLE_PRIMARY_KEYS,
)


class ArtistImage(BaseEntity):
    FIELD_META = ARTIST_IMAGES_TABLE_COL_META
    PRIMARY_KEYS = ARTIST_IMAGES_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ARTIST_IMAGES_TABLE_FOREIGN_KEYS
    TABLE_NAME = ARTIST_IMAGES_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_spotify_id: str | BasicFieldValue = UNSET,
        image_url: str | BasicFieldValue = UNSET,
        image_width: int | BasicFieldValue = UNSET,
        image_height: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "artist_id": artist_spotify_id,
            "url": image_url,
            "width": image_width,
            "height": image_height,
        }
        return cls._filter_fields(fields)

    def get_artist_id(self) -> str | BasicFieldValue:
        return getattr(self, "artist_id", UNSET)

    def get_url(self) -> str | BasicFieldValue:
        return getattr(self, "url", UNSET)


class AlbumImage(BaseEntity):
    FIELD_META = ALBUM_IMAGES_TABLE_COL_META
    PRIMARY_KEYS = ALBUM_IMAGES_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ALBUM_IMAGES_TABLE_FOREIGN_KEYS
    TABLE_NAME = ALBUM_IMAGES_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        album_spotify_id: str | BasicFieldValue = UNSET,
        image_url: str | BasicFieldValue = UNSET,
        image_width: int | BasicFieldValue = UNSET,
        image_height: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "album_id": album_spotify_id,
            "url": image_url,
            "width": image_width,
            "height": image_height,
        }
        return cls._filter_fields(fields)

    def get_album_id(self) -> str | BasicFieldValue:
        return getattr(self, "album_id", UNSET)

    def get_url(self) -> str | BasicFieldValue:
        return getattr(self, "url", UNSET)


class Album(BaseEntity):
    FIELD_META = ALBUMS_TABLE_COL_META
    PRIMARY_KEYS = ALBUMS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ALBUMS_TABLE_FOREIGN_KEYS
    TABLE_NAME = ALBUMS_TABLE_NAME

    def register_image(
        self,
        cur: sqlite3.Cursor,
        image: AlbumImage,
        simulate: bool = False,
    ) -> None:
        if self.get_id() != image.get_album_id():
            raise ValueError(err_msg("an image attached to an album must reference its album_id"))
        image.upsert_to_db(cur=cur, simulate=simulate)

    @classmethod
    def make_init_data(
        cls,
        *,
        album_spotify_id: str | BasicFieldValue = UNSET,
        album_title: str | BasicFieldValue = UNSET,
        album_genius_id: int | BasicFieldValue = UNSET,
        primary_artist_id: str | BasicFieldValue = UNSET,
        album_type: str | BasicFieldValue = UNSET,
        total_tracks: int | BasicFieldValue = UNSET,
        release_date: str | BasicFieldValue = UNSET,
        label: str | BasicFieldValue = UNSET,
        popularity: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "album_id": album_spotify_id,
            "title": album_title,
            "genius_id": album_genius_id,
            "primary_artist_id": primary_artist_id,
            "album_type": album_type,
            "total_tracks": total_tracks,
            "release_date": release_date,
            "label": label,
            "popularity": popularity,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> str | BasicFieldValue:
        return getattr(self, "album_id", UNSET)

    def get_genius_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)

    def get_primary_artist_id(self) -> str | BasicFieldValue:
        return getattr(self, "primary_artist_id", UNSET)


class Song(BaseEntity):
    FIELD_META = SONGS_TABLE_COL_META
    PRIMARY_KEYS = SONGS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = SONGS_TABLE_FOREIGN_KEYS
    TABLE_NAME = SONGS_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        track_spotify_id: str | BasicFieldValue = UNSET,
        track_title: str | BasicFieldValue = UNSET,
        song_genius_id: int | BasicFieldValue = UNSET,
        primary_artist_id: str | BasicFieldValue = UNSET,
        album_spotify_id: str | BasicFieldValue = UNSET,
        disc_number: int | BasicFieldValue = UNSET,
        track_number: int | BasicFieldValue = UNSET,
        duration_ms: int | BasicFieldValue = UNSET,
        explicit: bool | BasicFieldValue = UNSET,
        popularity: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "track_id": track_spotify_id,
            "title": track_title,
            "genius_id": song_genius_id,
            "primary_artist_id": primary_artist_id,
            "album_id": album_spotify_id,
            "disc_number": disc_number,
            "track_number": track_number,
            "duration_ms": duration_ms,
            "explicit": explicit,
            "popularity": popularity,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> str | BasicFieldValue:
        return getattr(self, "track_id", UNSET)

    def get_genius_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)

    def get_primary_artist_id(self) -> str | BasicFieldValue:
        return getattr(self, "primary_artist_id", UNSET)

    def get_album_id(self) -> str | BasicFieldValue:
        return getattr(self, "album_id", UNSET)


class DiscographyEntry(BaseEntity):
    FIELD_META = DISCOGRAPHY_TABLE_COL_META
    PRIMARY_KEYS = DISCOGRAPHY_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = DISCOGRAPHY_TABLE_FOREIGN_KEYS
    TABLE_NAME = DISCOGRAPHY_TABLE_NAME

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
        artist_spotify_id: str | BasicFieldValue = UNSET,
        track_spotify_id: str | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "artist_id": artist_spotify_id,
            "track_id": track_spotify_id,
        }
        return cls._filter_fields(fields)

    def get_artist_id(self) -> str | BasicFieldValue:
        return getattr(self, "artist_id", UNSET)

    def get_song_id(self) -> str | BasicFieldValue:
        return getattr(self, "track_id", UNSET)


class Artist(BaseEntity):
    FIELD_META = ARTISTS_TABLE_COL_META
    PRIMARY_KEYS = ARTISTS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ARTISTS_TABLE_FOREIGN_KEYS
    TABLE_NAME = ARTISTS_TABLE_NAME

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: Song,
        simulate: bool = False,
    ) -> None:
        entry = DiscographyEntry(
            data=DiscographyEntry.make_init_data(
                artist_spotify_id=self.get_id(),
                track_spotify_id=song.get_id(),
            )
        )
        entry.insert_to_db(cur=cur, simulate=simulate)

    def register_image(
        self,
        cur: sqlite3.Cursor,
        image: ArtistImage,
        simulate: bool = False,
    ) -> None:
        if self.get_id() != image.get_artist_id():
            raise ValueError(err_msg("an image attached to an artist must reference its artist_id"))
        image.upsert_to_db(cur=cur, simulate=simulate)

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_spotify_id: str | BasicFieldValue = UNSET,
        artist_name: str | BasicFieldValue = UNSET,
        artist_genius_id: int | BasicFieldValue = UNSET,
        total_followers: int | BasicFieldValue = UNSET,
        genres: str | BasicFieldValue = UNSET,
        popularity: int | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            "artist_id": artist_spotify_id,
            "name": artist_name,
            "genius_id": artist_genius_id,
            "total_followers": total_followers,
            "genres": genres,
            "popularity": popularity,
        }
        return cls._filter_fields(fields)

    def get_id(self) -> str | BasicFieldValue:
        return getattr(self, "artist_id", UNSET)

    def get_genius_id(self) -> int | BasicFieldValue:
        return getattr(self, "genius_id", UNSET)
