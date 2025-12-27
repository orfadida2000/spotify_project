import sqlite3

from sp2genius.utils import err_msg

from ..core.base import BinaryAssociationEntity, DependentRowEntity, SinglePkEntity
from ..core.constants import UNSET
from ..core.typing import BasicFieldValue
from ..genius.entities import GeniusAlbumInfo, GeniusArtistInfo, GeniusEntity, GeniusSongInfo
from .tables import (
    ALBUM_IMAGES_TABLE_FOREIGN_KEYS,
    ALBUM_IMAGES_TABLE_META,
    ALBUM_IMAGES_TABLE_NAME,
    ALBUM_IMAGES_TABLE_PRIMARY_KEYS,
    ALBUMS_TABLE_FOREIGN_KEYS,
    ALBUMS_TABLE_META,
    ALBUMS_TABLE_NAME,
    ALBUMS_TABLE_PRIMARY_KEYS,
    ARTIST_IMAGES_TABLE_FOREIGN_KEYS,
    ARTIST_IMAGES_TABLE_META,
    ARTIST_IMAGES_TABLE_NAME,
    ARTIST_IMAGES_TABLE_PRIMARY_KEYS,
    ARTISTS_TABLE_FOREIGN_KEYS,
    ARTISTS_TABLE_META,
    ARTISTS_TABLE_NAME,
    ARTISTS_TABLE_PRIMARY_KEYS,
    DISCOGRAPHY_TABLE_FOREIGN_KEYS,
    DISCOGRAPHY_TABLE_META,
    DISCOGRAPHY_TABLE_NAME,
    DISCOGRAPHY_TABLE_PRIMARY_KEYS,
    SONGS_TABLE_FOREIGN_KEYS,
    SONGS_TABLE_META,
    SONGS_TABLE_NAME,
    SONGS_TABLE_PRIMARY_KEYS,
)


class SpotifyEntity(SinglePkEntity):
    SPOTIFY_ENTITY_NAME: str | None = None
    _EXTRA_FREEZE_KEYS = ("SPOTIFY_ENTITY_NAME",)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        if "SPOTIFY_ENTITY_NAME" not in cls.__dict__:
            raise TypeError(
                err_msg(
                    f"Concrete subclass of SpotifyEntity must define SPOTIFY_ENTITY_NAME. "
                    f"Class '{cls.__name__}' does not."
                )
            )
        if not isinstance(cls.SPOTIFY_ENTITY_NAME, str):
            raise TypeError(
                err_msg(
                    f"SPOTIFY_ENTITY_NAME must be of type str. "
                    f"Class '{cls.__name__}' has SPOTIFY_ENTITY_NAME of type '{type(cls.SPOTIFY_ENTITY_NAME).__name__}'."
                )
            )
        cls.SPOTIFY_ENTITY_NAME = cls.SPOTIFY_ENTITY_NAME.strip().lower()
        if not cls.SPOTIFY_ENTITY_NAME:
            raise ValueError(
                err_msg(
                    f"SPOTIFY_ENTITY_NAME cannot be an empty string. "
                    f"Class '{cls.__name__}' has SPOTIFY_ENTITY_NAME set to an empty string."
                )
            )

    @classmethod
    def get_id_col_name(cls) -> str:
        return cls.get_pk_name()

    def get_id(self) -> str:
        return self.get_pk_value()

    def set_id(self, new_id: str) -> None:
        self.set_pk_value(new_id)

    @classmethod
    def get_spotify_url_col_name(cls) -> str:
        raise NotImplementedError(
            err_msg(
                "Spotify URL is based on the Spotify ID and serves as a virtual field, "
                "it is not stored directly in the database but generated dynamically on demand."
            )
        )

    def get_spotify_url(self) -> str:
        spotify_id = self.get_id()
        return f"https://open.spotify.com/{self.SPOTIFY_ENTITY_NAME}/{spotify_id}"

    def set_spotify_url(self, new_url: str) -> None:
        raise NotImplementedError(
            err_msg("The spotify url is based on the spotify id and cannot be set directly.")
        )

    @classmethod
    def get_genius_id_col_name(cls, genius_entity_cls: type[GeniusEntity]) -> str:
        return cls.get_fk_name_ref_single_pk_entity(genius_entity_cls)

    def get_genius_id(self, genius_entity_cls: type[GeniusEntity]) -> int | BasicFieldValue:
        return self.get_fk_value_ref_single_pk_entity(genius_entity_cls)

    def set_genius_id(
        self,
        new_id: int | BasicFieldValue,
        genius_entity_cls: type[GeniusEntity],
    ) -> None:
        self.set_fk_value_ref_single_pk_entity(genius_entity_cls, new_id)


class ArtistImage(DependentRowEntity):
    TABLE_META = ARTIST_IMAGES_TABLE_META
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
            cls.get_artist_id_col_name(): artist_spotify_id,
            cls.get_url_col_name(): image_url,
            "width": image_width,
            "height": image_height,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Artist)

    def get_artist_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Artist)

    def set_artist_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Artist, new_id)

    @classmethod
    def get_url_col_name(cls) -> str:
        pk_names_set = set(cls.get_pk_names())
        artist_id_col_name = cls.get_artist_id_col_name()
        assert artist_id_col_name in pk_names_set and len(pk_names_set) == 2, err_msg(
            "ArtistImage must have exactly two primary keys: artist_id and url."
        )
        pk_names_set.remove(artist_id_col_name)
        url_col_name = next(iter(pk_names_set))
        return url_col_name

    def get_url(self) -> str:
        url_col_name = self.get_url_col_name()
        return self.get_field_value(url_col_name)

    def set_url(self, new_url: str) -> None:
        url_col_name = self.get_url_col_name()
        self.set_field_value(url_col_name, new_url)


class AlbumImage(DependentRowEntity):
    TABLE_META = ALBUM_IMAGES_TABLE_META
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
            cls.get_album_id_col_name(): album_spotify_id,
            cls.get_url_col_name(): image_url,
            "width": image_width,
            "height": image_height,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_album_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Album)

    def get_album_id(self) -> str:
        album_id_col_name = self.get_album_id_col_name()
        return self.get_field_value(album_id_col_name)

    def set_album_id(self, new_id: str) -> None:
        album_id_col_name = self.get_album_id_col_name()
        self.set_field_value(album_id_col_name, new_id)

    @classmethod
    def get_url_col_name(cls) -> str:
        pk_names_set = set(cls.get_pk_names())
        album_id_col_name = cls.get_album_id_col_name()
        assert album_id_col_name in pk_names_set and len(pk_names_set) == 2, err_msg(
            "AlbumImage must have exactly two primary keys: album_id and url."
        )
        pk_names_set.remove(album_id_col_name)
        url_col_name = next(iter(pk_names_set))
        return url_col_name

    def get_url(self) -> str:
        url_col_name = self.get_url_col_name()
        return self.get_field_value(url_col_name)

    def set_url(self, new_url: str) -> None:
        url_col_name = self.get_url_col_name()
        self.set_field_value(url_col_name, new_url)


class Album(SpotifyEntity):
    TABLE_META = ALBUMS_TABLE_META
    PRIMARY_KEYS = ALBUMS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ALBUMS_TABLE_FOREIGN_KEYS
    TABLE_NAME = ALBUMS_TABLE_NAME
    SPOTIFY_ENTITY_NAME = "album"

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
            cls.get_id_col_name(): album_spotify_id,
            cls.get_title_col_name(): album_title,
            cls.get_genius_id_col_name(): album_genius_id,
            cls.get_primary_artist_id_col_name(): primary_artist_id,
            "album_type": album_type,
            "total_tracks": total_tracks,
            "release_date": release_date,
            "label": label,
            "popularity": popularity,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_genius_id_col_name(
        cls,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> str:
        return super().get_genius_id_col_name(GeniusAlbumInfo)

    def get_genius_id(
        self,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> int | BasicFieldValue:
        return super().get_genius_id(GeniusAlbumInfo)

    def set_genius_id(
        self,
        new_id: int | BasicFieldValue,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> None:
        super().set_genius_id(new_id, GeniusAlbumInfo)

    @classmethod
    def get_primary_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Artist)

    def get_primary_artist_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Artist)

    def set_primary_artist_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Artist, new_id)

    @classmethod
    def get_title_col_name(cls) -> str:
        return "title"

    def get_title(self) -> str:
        title_col_name = self.get_title_col_name()
        return self.get_field_value(title_col_name)

    def set_title(self, new_title: str) -> None:
        title_col_name = self.get_title_col_name()
        self.set_field_value(title_col_name, new_title)


class Song(SpotifyEntity):
    TABLE_META = SONGS_TABLE_META
    PRIMARY_KEYS = SONGS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = SONGS_TABLE_FOREIGN_KEYS
    TABLE_NAME = SONGS_TABLE_NAME
    SPOTIFY_ENTITY_NAME = "track"

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
            cls.get_id_col_name(): track_spotify_id,
            cls.get_title_col_name(): track_title,
            cls.get_genius_id_col_name(GeniusSongInfo): song_genius_id,
            cls.get_primary_artist_id_col_name(): primary_artist_id,
            cls.get_album_id_col_name(): album_spotify_id,
            cls.get_disc_number_col_name(): disc_number,
            cls.get_track_number_col_name(): track_number,
            "duration_ms": duration_ms,
            "explicit": explicit,
            "popularity": popularity,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_genius_id_col_name(cls, genius_entity_cls: type[GeniusEntity] | None = None) -> str:
        return super().get_genius_id_col_name(GeniusSongInfo)

    def get_genius_id(
        self,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> int | BasicFieldValue:
        return super().get_genius_id(GeniusSongInfo)

    def set_genius_id(
        self,
        new_id: int | BasicFieldValue,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> None:
        super().set_genius_id(new_id, GeniusSongInfo)

    @classmethod
    def get_primary_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Artist)

    def get_primary_artist_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Artist)

    def set_primary_artist_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Artist, new_id)

    @classmethod
    def get_album_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Album)

    def get_album_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Album)

    def set_album_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Album, new_id)

    @classmethod
    def get_title_col_name(cls) -> str:
        return "title"

    def get_title(self) -> str:
        title_col_name = self.get_title_col_name()
        return self.get_field_value(title_col_name)

    def set_title(self, new_title: str) -> None:
        title_col_name = self.get_title_col_name()
        self.set_field_value(title_col_name, new_title)

    @classmethod
    def get_disc_number_col_name(cls) -> str:
        return "disc_number"

    def get_disc_number(self) -> int:
        disc_number_col_name = self.get_disc_number_col_name()
        return self.get_field_value(disc_number_col_name)

    def set_disc_number(self, new_disc_number: int) -> None:
        disc_number_col_name = self.get_disc_number_col_name()
        self.set_field_value(disc_number_col_name, new_disc_number)

    @classmethod
    def get_track_number_col_name(cls) -> str:
        return "track_number"

    def get_track_number(self) -> int:
        track_number_col_name = self.get_track_number_col_name()
        return self.get_field_value(track_number_col_name)

    def set_track_number(self, new_track_number: int) -> None:
        track_number_col_name = self.get_track_number_col_name()
        self.set_field_value(track_number_col_name, new_track_number)


class DiscographyEntry(BinaryAssociationEntity):
    TABLE_META = DISCOGRAPHY_TABLE_META
    PRIMARY_KEYS = DISCOGRAPHY_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = DISCOGRAPHY_TABLE_FOREIGN_KEYS
    TABLE_NAME = DISCOGRAPHY_TABLE_NAME

    @classmethod
    def make_init_data(
        cls,
        *,
        artist_spotify_id: str | BasicFieldValue = UNSET,
        track_spotify_id: str | BasicFieldValue = UNSET,
    ) -> dict:
        fields = {
            cls.get_artist_id_col_name(): artist_spotify_id,
            cls.get_song_id_col_name(): track_spotify_id,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_artist_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Artist)

    def get_artist_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Artist)

    def set_artist_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Artist, new_id)

    @classmethod
    def get_song_id_col_name(cls) -> str:
        return cls.get_fk_name_ref_single_pk_entity(Song)

    def get_song_id(self) -> str:
        return self.get_fk_value_ref_single_pk_entity(Song)

    def set_song_id(self, new_id: str) -> None:
        self.set_fk_value_ref_single_pk_entity(Song, new_id)


class Artist(SpotifyEntity):
    TABLE_META = ARTISTS_TABLE_META
    PRIMARY_KEYS = ARTISTS_TABLE_PRIMARY_KEYS
    FOREIGN_KEYS = ARTISTS_TABLE_FOREIGN_KEYS
    TABLE_NAME = ARTISTS_TABLE_NAME
    SPOTIFY_ENTITY_NAME = "artist"

    def register_discography_entry(
        self,
        cur: sqlite3.Cursor,
        song: Song,
        simulate: bool = False,
    ) -> None:
        entry_data = DiscographyEntry.make_init_data(
            artist_spotify_id=self.get_id(),
            track_spotify_id=song.get_id(),
        )
        entry = DiscographyEntry(data=entry_data)
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
            cls.get_id_col_name(): artist_spotify_id,
            cls.get_name_col_name(): artist_name,
            cls.get_genius_id_col_name(): artist_genius_id,
            "total_followers": total_followers,
            "genres": genres,
            "popularity": popularity,
        }
        return cls._filter_data(fields)

    @classmethod
    def get_genius_id_col_name(cls, genius_entity_cls: type[GeniusEntity] | None = None) -> str:
        return super().get_genius_id_col_name(GeniusArtistInfo)

    def get_genius_id(
        self,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> int | BasicFieldValue:
        return super().get_genius_id(GeniusArtistInfo)

    def set_genius_id(
        self,
        new_id: int | BasicFieldValue,
        genius_entity_cls: type[GeniusEntity] | None = None,
    ) -> None:
        super().set_genius_id(new_id, GeniusArtistInfo)

    @classmethod
    def get_name_col_name(cls) -> str:
        return "name"

    def get_name(self) -> str:
        name_col_name = self.get_name_col_name()
        return self.get_field_value(name_col_name)

    def set_name(self, new_name: str) -> None:
        name_col_name = self.get_name_col_name()
        self.set_field_value(name_col_name, new_name)
