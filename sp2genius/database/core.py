import sqlite3
from textwrap import dedent
from typing import Final, TypeAlias

CONCAT = "||"  # SQLite string concatenation operator
FOREIGN_KEYS = True
_YEAR_GLOB = r"[0-9][0-9][0-9][0-9]"
_MONTH_GLOB = r"[0-9][0-9]"
_DAY_GLOB = r"[0-9][0-9]"

_ISO_YEAR_GLOB = f"{_YEAR_GLOB}"
CHECK_ISO_YEAR_GLOB = lambda col: f"length({col}) = 4 AND {col} GLOB '{_ISO_YEAR_GLOB}'"

_ISO_YEAR_MONTH_GLOB = f"{_YEAR_GLOB}-{_MONTH_GLOB}"
CHECK_ISO_YEAR_MONTH_GLOB = lambda col: f"length({col}) = 7 AND {col} GLOB '{_ISO_YEAR_MONTH_GLOB}'"

_ISO_FULL_DATE_GLOB = f"{_YEAR_GLOB}-{_MONTH_GLOB}-{_DAY_GLOB}"
CHECK_ISO_FULL_DATE_GLOB = lambda col: f"length({col}) = 10 AND {col} GLOB '{_ISO_FULL_DATE_GLOB}'"

_ALPHANUMERIC_GLOB = r"[A-Za-z0-9]"
CHECK_ALPHANUMERIC_GLOB = lambda col: f"{col} GLOB '{_ALPHANUMERIC_GLOB}*'"

_BASE64_URL_SAFE_GLOB = r"[A-Za-z0-9_-]"
CHECK_BASE64_URL_SAFE_GLOB = lambda col: f"{col} GLOB '{_BASE64_URL_SAFE_GLOB}*'"


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET: Final[_UnsetType] = _UnsetType()

BasicFieldValue: TypeAlias = None | _UnsetType


class BaseEntity:
    FIELD_META: dict[str, tuple[bool, type]] = {}  # to be overridden in subclasses
    PRIMARY_KEYS: tuple[str, ...] = ()  # to be overridden in subclasses
    TABLE_NAME: str = ""  # to be overridden in subclasses

    def __init_subclass__(cls, **kwargs):  # noqa: ANN003
        super().__init_subclass__(**kwargs)

        # All subclasses must define FIELD_META
        if not isinstance(cls.FIELD_META, dict):
            raise TypeError(f"{cls.__name__}.FIELD_META must be a dict")
        if not all(
            isinstance(k, str)
            and isinstance(v, tuple)
            and len(v) == 2
            and isinstance(v[0], bool)
            and isinstance(v[1], type)
            and v[1] is not type(None)
            for k, v in cls.FIELD_META.items()
        ):
            raise TypeError(f"{cls.__name__}.FIELD_META must be a dict[str, tuple[bool, type]]")
        if not cls.FIELD_META:
            raise TypeError(f"{cls.__name__} must define a non-empty FIELD_META")

        if not isinstance(cls.PRIMARY_KEYS, tuple):
            raise TypeError(f"{cls.__name__}.PRIMARY_KEYS must be a tuple")
        if not all(isinstance(pk, str) for pk in cls.PRIMARY_KEYS):
            raise TypeError(f"{cls.__name__}.PRIMARY_KEYS must be a tuple of strings")
        if not cls.PRIMARY_KEYS:
            raise TypeError(f"{cls.__name__} must define a non-empty PRIMARY_KEYS")

        if not isinstance(cls.TABLE_NAME, str):
            raise TypeError(f"{cls.__name__}.TABLE_NAME must be a string")
        cls.TABLE_NAME = cls.TABLE_NAME.strip()
        if not cls.TABLE_NAME:
            raise TypeError(f"{cls.__name__} must define a non-empty TABLE_NAME")

        for pk_col in cls.PRIMARY_KEYS:
            if pk_col not in cls.FIELD_META:
                raise ValueError(
                    f"{cls.__name__}: PRIMARY_KEYS contains '{pk_col}' which is not in FIELD_META"
                )
            is_required = cls.FIELD_META[pk_col][0]
            if not is_required:
                raise ValueError(
                    f"{cls.__name__}: PRIMARY_KEYS contains '{pk_col}' "
                    "which is not marked as required in FIELD_META"
                )

        # Compute per-class static attributes from FIELD_META
        cls.FIELDS = tuple(cls.FIELD_META.keys())
        cls.REQUIRED_FIELDS = tuple(
            (f, f_type) for f, (required, f_type) in cls.FIELD_META.items() if required
        )
        cls.OPTIONAL_FIELDS = tuple(
            (f, (f_type, type(None)))
            for f, (required, f_type) in cls.FIELD_META.items()
            if not required
        )
        cls.__slots__ = cls.FIELDS  # or tuple(cls.FIELDS)

    @classmethod
    def _validate_insert_data(cls, data: dict) -> None:
        required = {field for field, _ in cls.REQUIRED_FIELDS}
        provided = set(data.keys())
        missing = required - provided
        if missing:
            raise ValueError(
                f"{cls.__name__}.insert_to_db: missing required fields for INSERT: {missing}"
            )

    @classmethod
    def _filter_fields(cls, fields: dict) -> dict:
        assert set(fields.keys()) == set(cls.FIELDS), "Mismatch between fields and init data keys"
        filtered_fields = {k: v for k, v in fields.items() if v is not UNSET}
        return filtered_fields

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
        for field, field_type in self.REQUIRED_FIELDS:
            if field in data:
                if data[field] is None:
                    raise ValueError(
                        f"{self.__class__.__name__}.__init__: required field '{field}' is None"
                    )
                elif not isinstance(data[field], field_type):
                    raise TypeError(
                        f"{self.__class__.__name__}.__init__: field '{field}' must be of type"
                        f" {field_type.__name__}, got {type(data[field]).__name__} instead"
                    )
                setattr(self, field, data[field])
            elif field in self.PRIMARY_KEYS:
                raise ValueError(
                    f"{self.__class__.__name__}.__init__: required primary key field '{field}' is missing"
                )
        for field, field_type in self.OPTIONAL_FIELDS:
            if field in data:
                if not isinstance(data[field], field_type):
                    raise TypeError(
                        f"{self.__class__.__name__}.__init__: field '{field}' must be None or of type"
                        f" {field_type[0].__name__}, got {type(data[field]).__name__} instead"
                    )
                setattr(self, field, data[field])

    def curr_state_dict(self) -> dict:
        data = {}
        for field, field_type in self.REQUIRED_FIELDS:
            if hasattr(self, field):
                field_value = getattr(self, field)
                if field_value is None:
                    raise ValueError(
                        f"{self.__class__.__name__}.state_dict: required field '{field}' is None"
                    )
                elif not isinstance(field_value, field_type):
                    raise TypeError(
                        f"{self.__class__.__name__}.state_dict: field '{field}' must be of type"
                        f" {field_type.__name__}, got {type(field_value).__name__} instead"
                    )
                data[field] = field_value
            elif field in self.PRIMARY_KEYS:
                raise ValueError(
                    f"{self.__class__.__name__}.state_dict: required primary key field '{field}' is missing"
                )
        for field, field_type in self.OPTIONAL_FIELDS:
            if hasattr(self, field):
                field_value = getattr(self, field)
                if not isinstance(field_value, field_type):
                    raise TypeError(
                        f"{self.__class__.__name__}.state_dict: field '{field}' must be None or of type"
                        f" {field_type[0].__name__}, got {type(field_value).__name__} instead"
                    )
                data[field] = field_value
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
