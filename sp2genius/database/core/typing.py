from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import ClassVar, Final, TypeAlias

from sp2genius.database.core.sql.utils import sanitize_sql_identifier

CreateStatement: TypeAlias = str
FieldName: TypeAlias = str
FieldNullability: TypeAlias = bool
FieldUniqueness: TypeAlias = bool
TableName: TypeAlias = str
PrimaryKeyNames: TypeAlias = tuple[FieldName, ...]
RefMapping: TypeAlias = dict[FieldName, FieldName]
ForeignKeyMapping: TypeAlias = dict[TableName, RefMapping]


def type_lookups(cls: type["SqlColType"]) -> type["SqlColType"]:
    py_to_sql_map: dict[type, SqlColType] = {
        str: cls.TEXT,
        int: cls.INTEGER,
        float: cls.REAL,
        bytes: cls.BLOB,
        bytearray: cls.BLOB,
        memoryview: cls.BLOB,
        bool: cls.BOOLEAN,
    }
    cls.__PY_TO_SQL_TYPE_MAP = MappingProxyType(py_to_sql_map)

    sql_to_py_map: dict[SqlColType, list[type]] = {}
    for py_type, sql_type in py_to_sql_map.items():
        if sql_type not in sql_to_py_map:
            sql_to_py_map[sql_type] = []
        sql_to_py_map[sql_type].append(py_type)

    sql_to_py_map_final = {
        sql_type: tuple(py_types) for sql_type, py_types in sql_to_py_map.items()
    }
    cls.__SQL_TO_PY_TYPE_MAP = MappingProxyType(sql_to_py_map_final)

    return cls


@type_lookups
class SqlColType(Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEAN = "INTEGER "  # SQLite stores booleans as integers (0/1)

    __PY_TO_SQL_TYPE_MAP: MappingProxyType[type, "SqlColType"]
    __SQL_TO_PY_TYPE_MAP: MappingProxyType["SqlColType", tuple[type, ...]]

    @property
    def declared_type(self) -> str:
        return self.value.strip()

    @classmethod
    def sql_col_type_from_py_type(cls, py_type: type) -> "SqlColType":
        assert isinstance(py_type, type), f"py_type must be a type, got: {type(py_type)}"
        if py_type not in cls.__PY_TO_SQL_TYPE_MAP:
            raise ValueError(f"No corresponding ColType for Python type: {py_type}")
        return cls.__PY_TO_SQL_TYPE_MAP[py_type]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldMeta:
    py_type: type
    nullable: FieldNullability = True
    unique: FieldUniqueness = False
    sql_type: SqlColType = field(init=False)

    _NULL_TYPE: ClassVar[type] = type(None)

    def allowed_types(self) -> tuple[type, ...]:
        if self.nullable:
            return (self.py_type, self._NULL_TYPE)
        return (self.py_type,)

    def is_valid_value(self, value: object) -> bool:
        return isinstance(value, self.allowed_types())

    def get_py_type(self) -> type:
        return self.py_type

    def get_nullability(self) -> FieldNullability:
        return self.nullable

    def get_uniqueness(self) -> FieldUniqueness:
        return self.unique

    def get_sql_type(self) -> SqlColType:
        return self.sql_type

    def __post_init__(self) -> None:
        if not isinstance(self.get_py_type(), type):
            raise TypeError(f"py_type must be a type, got: {type(self.get_py_type())}")
        if self.get_py_type() is self._NULL_TYPE:
            raise ValueError("py_type cannot be NoneType")
        if not isinstance(self.get_nullability(), bool):
            raise TypeError(f"nullable must be bool, got: {type(self.get_nullability())}")
        if not isinstance(self.get_uniqueness(), bool):
            raise TypeError(f"unique must be bool, got: {type(self.get_uniqueness())}")

        sql_type = SqlColType.sql_col_type_from_py_type(self.get_py_type())
        object.__setattr__(self, "sql_type", sql_type)


TableMeta: TypeAlias = dict[FieldName, FieldMeta]


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


BasicFieldValue: TypeAlias = None | _UnsetType

# UNSET Singleton Instance
UNSET: Final[_UnsetType] = _UnsetType()


@dataclass(frozen=True, slots=True, kw_only=True)
class TableColumn:
    name: str
    sql_type: SqlColType
    nullable: bool = True
    unique: bool = False

    def __post_init__(self) -> None:
        norm_name = sanitize_sql_identifier(self.name, strict=True)
        object.__setattr__(self, "name", norm_name)
        if not isinstance(self.sql_type, SqlColType):
            raise TypeError(f"sql_type must be SqlColType, got: {type(self.sql_type)}")
        if not isinstance(self.nullable, bool):
            raise TypeError(f"nullable must be bool, got: {type(self.nullable)}")
        if not isinstance(self.unique, bool):
            raise TypeError(f"unique must be bool, got: {type(self.unique)}")

    def pk_col_normalization(self, single_pk: bool = False) -> None:
        """
        If this column is part of a primary key, adjust its properties accordingly.
        Must be called from outside by schema aware caller.
        It sets nullable to False unconditionally as PK columns cannot be NULL.
        If single_pk is True, it also sets unique to False as it is redundant for single-column PKs,
        otherwise unique remains as is (for composite PKs, uniqueness is enforced by the PK constraint).
        """
        object.__setattr__(self, "nullable", False)
        if single_pk:
            object.__setattr__(self, "unique", False)


class TableSchema:
    pass
