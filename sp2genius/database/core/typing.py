from dataclasses import dataclass
from typing import Final, TypeAlias

_NONE_TYPE: Final[type] = type(None)

CreateStatement: TypeAlias = str
FieldName: TypeAlias = str
FieldNullability: TypeAlias = bool
TableName: TypeAlias = str
PrimaryKeyNames: TypeAlias = tuple[FieldName, ...]
RefMapping: TypeAlias = dict[FieldName, FieldName]
ForeignKeyMapping: TypeAlias = dict[TableName, RefMapping]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldMeta:
    py_type: type
    nullable: FieldNullability

    def allowed_types(self) -> tuple[type, ...]:
        if self.nullable:
            return (self.py_type, _NONE_TYPE)
        return (self.py_type,)

    def is_valid_value(self, value: object) -> bool:
        return isinstance(value, self.allowed_types())


TableMeta: TypeAlias = dict[FieldName, FieldMeta]


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


BasicFieldValue: TypeAlias = None | _UnsetType
