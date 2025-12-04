import sqlite3
from textwrap import dedent

from .schema import (
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


class BaseEntity:
    FIELD_META: dict[str, object] = {}  # to be overridden in subclasses
    PRIMARY_KEYS: tuple[str, ...] = ()  # to be overridden in subclasses
    TABLE_NAME: str = ""  # to be overridden in subclasses

    def __init_subclass__(cls, **kwargs):  # noqa: ANN003
        super().__init_subclass__(**kwargs)

        # All subclasses must define FIELD_META
        if not cls.FIELD_META:
            raise TypeError(f"{cls.__name__} must define FIELD_META")
        if not cls.PRIMARY_KEYS:
            raise TypeError(f"{cls.__name__} must define PRIMARY_KEYS")
        if not cls.TABLE_NAME:
            raise TypeError(f"{cls.__name__} must define TABLE_NAME")
        for pk_col in cls.PRIMARY_KEYS:
            if pk_col not in cls.FIELD_META:
                raise ValueError(
                    f"{cls.__name__}: PRIMARY_KEYS contains '{pk_col}' which is not in FIELD_META"
                )
            elif not cls.FIELD_META[pk_col]:
                raise ValueError(
                    f"{cls.__name__}: PRIMARY_KEYS contains '{pk_col}' "
                    "which is not marked as required in FIELD_META"
                )

        # Compute per-class static attributes from FIELD_META
        cls.FIELDS = tuple(cls.FIELD_META.keys())
        cls.REQUIRED_FIELDS = tuple(f for f, required in cls.FIELD_META.items() if required)
        cls.OPTIONAL_FIELDS = tuple(f for f, required in cls.FIELD_META.items() if not required)
        cls.__slots__ = cls.FIELDS  # or tuple(cls.FIELDS)

    @classmethod
    def _validate_insert_data(cls, data: dict) -> None:
        required = set(cls.REQUIRED_FIELDS)
        provided = set(data.keys())
        missing = required - provided
        if missing:
            raise ValueError(
                f"{cls.__name__}.insert_to_db: missing required fields for INSERT: {missing}"
            )

    @staticmethod
    def _simulate_sql_exc(sql: str, data: dict) -> None:
        sql = sql.strip()
        print(f"[SIMULATE] Executing SQL:\n{sql}\n")
        print("[SIMULATE] With data:")
        print("{")
        data_len = len(data)
        count = 1
        for k, v in data.items():
            if v is None:
                v = "NULL"
            if count == data_len:
                print(f'  "{k}": {v}')
            else:
                print(f'  "{k}": {v},')
            count += 1
        print("}")
        print()

    def __init__(self, data: dict):
        for field in self.REQUIRED_FIELDS:
            if field in data:
                if data[field] is None:
                    raise ValueError(
                        f"{self.__class__.__name__}.__init__: required field '{field}' is None"
                    )
                setattr(self, field, data[field])
            elif field in self.PRIMARY_KEYS:
                raise ValueError(
                    f"{self.__class__.__name__}.__init__: required primary key field '{field}' is missing"
                )
        for field in self.OPTIONAL_FIELDS:
            if field in data:
                setattr(self, field, data[field])

    def curr_state_dict(self) -> dict:
        data = {}
        for field in self.REQUIRED_FIELDS:
            if hasattr(self, field):
                if getattr(self, field) is None:
                    raise ValueError(
                        f"{self.__class__.__name__}.state_dict: required field '{field}' is None"
                    )
                data[field] = getattr(self, field)
            elif field in self.PRIMARY_KEYS:
                raise ValueError(
                    f"{self.__class__.__name__}.state_dict: required primary key field '{field}' is missing"
                )
        for field in self.OPTIONAL_FIELDS:
            if hasattr(self, field):
                data[field] = getattr(self, field)
        return data

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        if not simulate and not cur:
            raise ValueError(f"{self.__class__.__name__}.insert_to_db: 'cur' is required")

        data = self.curr_state_dict()
        self._validate_insert_data(data)
        cols = ",\n    ".join(data.keys())
        placeholders = ",\n    ".join(f":{col}" for col in data.keys())
        sql = dedent(f"""
        INSERT INTO {self.TABLE_NAME} (
            {cols}
        ) VALUES (
            {placeholders}
        )
        """)
        if on_conflict:
            pks = ", ".join(self.PRIMARY_KEYS)
            sql += f"ON CONFLICT({pks}) DO NOTHING"
        if not simulate:
            cur.execute(sql, data)
        else:
            self._simulate_sql_exc(sql, data)

    def update_fields_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
    ) -> bool:
        if not simulate and not cur:
            raise ValueError(f"{self.__class__.__name__}.update_fields_db: 'cur' is required")

        data = self.curr_state_dict()
        update_cols = [k for k in data.keys() if k not in self.PRIMARY_KEYS]
        if not update_cols:
            return False  # nothing to update
        set_clause = ",\n    ".join(f"{col} = :{col}" for col in update_cols)
        where_clause = " AND\n    ".join(f"{pk_col} = :{pk_col}" for pk_col in self.PRIMARY_KEYS)
        sql = dedent(f"""
        UPDATE {self.TABLE_NAME}
        SET
            {set_clause}
        WHERE
            {where_clause}
        """)
        if not simulate:
            cur.execute(sql, data)
            if cur.rowcount > 0:
                return True  # row existed and has been patched
        else:
            self._simulate_sql_exc(sql, data)
        return False

    def upsert_to_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> None:
        if not simulate and not cur:
            raise ValueError(f"{self.__class__.__name__}.upsert_to_db: 'cur' is required")

        # 1) Try UPDATE (patch existing row)
        row_updated = self.update_fields_db(cur=cur, simulate=simulate)
        if row_updated:
            return

        # 2) If no row was updated, try INSERT with the provided columns
        self.insert_to_db(cur=cur, simulate=simulate, on_conflict=False)

    def exists_in_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        if not simulate and not cur:
            raise ValueError(f"{self.__class__.__name__}.exists_in_db: 'cur' is required")

        data = self.curr_state_dict()
        where_clause = " AND\n    ".join(f"{pk_col} = :{pk_col}" for pk_col in self.PRIMARY_KEYS)
        sql = dedent(f"""
        SELECT 1 FROM {self.TABLE_NAME}
        WHERE
            {where_clause}
        LIMIT 1
        """)
        if not simulate:
            cur.execute(sql, data)
            row = cur.fetchone()
            return row is not None
        else:
            self._simulate_sql_exc(sql, data)
            return False


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
