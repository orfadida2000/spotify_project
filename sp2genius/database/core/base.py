import sqlite3
from collections.abc import ItemsView, Iterable, KeysView, ValuesView
from textwrap import dedent
from types import MappingProxyType
from typing import Any, Final

from sp2genius.utils import err_msg

from .constants import UNSET
from .typing import (
    FieldMeta,
    FieldName,
    ForeignKeyMapping,
    PrimaryKeyNames,
    RefMapping,
    TableMeta,
    TableName,
)
from .utils import is_valid_identifier


class EntityMeta(type):
    # Static attribute name for concrete entity flag
    CONCRETE_ENTITY_FLAG_ATTR: Final[str] = "_CONCRETE_ENTITY"

    # class-body baseline knobs (both-or-none)
    BASE_FREEZE_KEYS_ATTR: Final[str] = "_BASE_FREEZE_KEYS"  # iterable[str]
    BASE_SLOTS_SOURCE_NAME_ATTR: Final[str] = "_BASE_SLOTS_SOURCE_NAME"  # str (e.g. "SCHEMA_META")

    # class-body extension knob (optional)
    EXTRA_FREEZE_KEYS_ATTR: Final[str] = "_EXTRA_FREEZE_KEYS"  # iterable[str]

    # metaclass-injected internal attrs (must not appear in class body)
    _DERIVED_FREEZE_KEYS_ATTR: Final[str] = "_DERIVED_FREEZE_KEYS"  # frozenset[str]
    _DERIVED_SLOTS_SOURCE_NAME_ATTR: Final[str] = "_DERIVED_SLOTS_SOURCE_NAME"  # str

    @staticmethod
    def _get_extra_freeze_keys(
        mcls: type["EntityMeta"],
        *,
        name: str,
        namespace: dict[str, object],
    ) -> set[str]:
        if mcls.EXTRA_FREEZE_KEYS_ATTR not in namespace:
            return set()

        extra_freeze_keys = namespace[mcls.EXTRA_FREEZE_KEYS_ATTR]
        if not mcls._is_allowed_iterable(extra_freeze_keys, allow_str_like=False):
            raise TypeError(
                err_msg(
                    f"the class is invalidly defined, '{mcls.EXTRA_FREEZE_KEYS_ATTR}' must be a native iterable, got {type(extra_freeze_keys).__name__}"
                )
            )
        mcls._identifiers_validation(
            mcls,
            names_iterable=extra_freeze_keys,  # pyright: ignore[reportArgumentType]
            iterable_name=mcls.EXTRA_FREEZE_KEYS_ATTR,
            provider_name=name,
            err_prefix="error,",
            inherited=False,
        )
        return set(extra_freeze_keys)  # pyright: ignore[reportArgumentType]

    @staticmethod
    def _resolve_single_provider(
        *,
        bases: tuple[type, ...],
        names: tuple[str, ...],
    ) -> type | None:
        """
        Resolve all `names` from exactly one provider:
        - one base class' __dict__ (via MRO, all-or-nothing)

        Returns a the provider class object if found,
        Returns None if no provider was found.
        """

        # Search bases' MRO for a single provider class
        seen: set[type] = set()

        for base in bases:
            for cls in base.__mro__:
                if cls in seen:
                    continue
                seen.add(cls)

                d = cls.__dict__
                if all(name in d for name in names):
                    return cls

        return None

    @staticmethod
    def _freeze(mcls: type["EntityMeta"], obj: object) -> Any:
        if isinstance(obj, dict):
            return MappingProxyType({k: mcls._freeze(mcls, v) for k, v in obj.items()})

        if isinstance(obj, KeysView):
            return tuple(obj)

        if isinstance(obj, ItemsView):
            return tuple((k, mcls._freeze(mcls, v)) for k, v in obj)

        if isinstance(obj, (list, tuple, range, ValuesView)):
            return tuple(mcls._freeze(mcls, v) for v in obj)

        if isinstance(obj, (set, frozenset)):
            return frozenset(obj)

        if isinstance(obj, bytearray):
            return bytes(obj)

        return obj

    @classmethod
    def frozen_type(mcls, obj: Any, by_type: bool = False) -> type:  # noqa: N804
        if by_type and not isinstance(obj, type):
            raise TypeError(err_msg("by_type=True requires obj to be a type"))

        if (not by_type and isinstance(obj, dict)) or (by_type and obj is dict):
            return MappingProxyType

        if (not by_type and isinstance(obj, KeysView)) or (by_type and obj is KeysView):
            return tuple

        if (not by_type and isinstance(obj, ItemsView)) or (by_type and obj is ItemsView):
            return tuple

        if (not by_type and isinstance(obj, (list, tuple, range, ValuesView))) or (
            by_type and any(obj is t for t in (list, tuple, range, ValuesView))
        ):
            return tuple

        if (not by_type and isinstance(obj, (set, frozenset))) or (
            by_type and any(obj is t for t in (set, frozenset))
        ):
            return frozenset

        if (not by_type and isinstance(obj, bytearray)) or (by_type and obj is bytearray):
            return bytes

        if by_type:
            return obj
        else:
            return type(obj)

    @staticmethod
    def _is_allowed_iterable(obj: object, allow_str_like: bool = False) -> bool:
        """
        Check if an object is of an allowed iterable type.
        Allowed iterables are considered to be of type:
            - list, tuple
            - set, frozenset
            - dict, KeysView, ValuesView, ItemsView
            - range
            - str, bytes, bytearray (if allow_str_like is True)


        Arguments:
            obj: The object to check.
            allow_str_like: If True, also consider str and bytes as native iterables.

        Returns:
            True if the object is a native iterable, False otherwise.
        """
        native_non_str_iter_types = (
            list,
            tuple,
            set,
            frozenset,
            dict,
            KeysView,
            ValuesView,
            ItemsView,
            range,
        )
        native_str_iter_types = (
            str,
            bytes,
            bytearray,
        )
        if allow_str_like:
            return isinstance(obj, native_non_str_iter_types + native_str_iter_types)
        return isinstance(obj, native_non_str_iter_types)

    @staticmethod
    def _identifier_validation(
        *,
        name: object,
        err_prefix: str,
    ) -> None:
        err_prefix = err_prefix.strip()
        if not err_prefix:
            err_prefix = "error,"

        is_identifier = is_valid_identifier(name)
        if is_identifier == 1:
            raise TypeError(err_msg(f"{err_prefix} non-str name of type {type(name).__name__}"))
        elif is_identifier == 2:
            raise ValueError(err_msg(f"{err_prefix} empty string name"))
        elif is_identifier == 3:
            raise ValueError(err_msg(rf"{err_prefix} invalid python identifier \"{name}\""))
        elif is_identifier == 4:
            raise ValueError(err_msg(rf"{err_prefix} python keyword \"{name}\""))

    @staticmethod
    def _identifiers_validation(
        mcls: type["EntityMeta"],
        *,
        names_iterable: Iterable[object],
        iterable_name: str,
        provider_name: str,
        err_prefix: str = "",
        inherited: bool = False,
    ) -> None:
        err_prefix = err_prefix.strip()
        if not err_prefix:
            err_prefix = "error,"

        if not inherited:
            base_err = f"{err_prefix} the class {provider_name} defines an invalid '{iterable_name}', it contains"
        else:
            base_err = f"{err_prefix} the provider class {provider_name} provides an invalid '{iterable_name}', it contains"

        for name in names_iterable:
            mcls._identifier_validation(
                name=name,
                err_prefix=base_err,
            )

    @staticmethod
    def _baseline_mode(
        mcls: type["EntityMeta"],
        *,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> tuple[set[str], str, tuple[str, ...]]:
        def _baseline_mode_validation() -> None:
            err_prefix = f"base-mode contract violation for the class {name},"
            base_freeze_keys = namespace[mcls.BASE_FREEZE_KEYS_ATTR]
            base_slots_source_name = namespace[mcls.BASE_SLOTS_SOURCE_NAME_ATTR]

            # Validate base_freeze_keys
            if not mcls._is_allowed_iterable(base_freeze_keys, allow_str_like=False):
                raise TypeError(
                    err_msg(
                        f"{err_prefix} the class {name} is invalidly defined, '{mcls.BASE_FREEZE_KEYS_ATTR}' must be a native iterable, got {type(base_freeze_keys).__name__}"
                    )
                )
            mcls._identifiers_validation(
                mcls,
                names_iterable=base_freeze_keys,  # pyright: ignore[reportArgumentType]
                iterable_name=mcls.BASE_FREEZE_KEYS_ATTR,
                provider_name=name,
                err_prefix=err_prefix,
                inherited=False,
            )

            # Validate base_slots_source_name
            mcls._identifier_validation(
                name=base_slots_source_name,
                err_prefix=f"{err_prefix} the class {name} defines an invalid '{mcls.BASE_SLOTS_SOURCE_NAME_ATTR}',",
            )
            if base_slots_source_name not in namespace:
                raise ValueError(
                    err_msg(
                        f"{err_prefix} the class {name} is invalidly defined, '{mcls.BASE_SLOTS_SOURCE_NAME_ATTR}' refers to a non-existent attribute: '{base_slots_source_name}'"
                    )
                )

            # Validate base_slots_source_name value
            base_slots_src = namespace[base_slots_source_name]  # pyright: ignore[reportArgumentType]
            if base_slots_src is not None:
                if not mcls._is_allowed_iterable(base_slots_src, allow_str_like=False):
                    raise TypeError(
                        err_msg(
                            f"{err_prefix} the class {name} is invalidly defined, the base slots source attribute '{base_slots_source_name}' must be None or a native iterable, got {type(base_slots_src).__name__}"
                        )
                    )
                mcls._identifiers_validation(
                    mcls,
                    names_iterable=base_slots_src,  # pyright: ignore[reportArgumentType]
                    iterable_name=base_slots_source_name,  # pyright: ignore[reportArgumentType]
                    provider_name=name,
                    err_prefix=err_prefix,
                    inherited=False,
                )

        _baseline_mode_validation()
        base_freeze_keys: Iterable[str] = namespace[mcls.BASE_FREEZE_KEYS_ATTR]
        base_slots_source_name: str = namespace[mcls.BASE_SLOTS_SOURCE_NAME_ATTR]
        base_slots_src: Iterable[str] | None = namespace[base_slots_source_name]

        # Process freeze keys
        extra_freeze_keys: set[str] = mcls._get_extra_freeze_keys(
            mcls,
            name=name,
            namespace=namespace,
        )
        base_freeze_keys_set: set[str] = set(base_freeze_keys)
        internal_freeze_keys_set: set[str] = {
            mcls._DERIVED_FREEZE_KEYS_ATTR,
            mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR,
            "__slots__",
        }
        total_freeze_keys_set: set[str] = (
            base_freeze_keys_set | extra_freeze_keys | internal_freeze_keys_set
        )

        # Process slots
        if base_slots_src is None:
            slots_tuple: tuple[str, ...] = ()
        else:
            slots_tuple: tuple[str, ...] = tuple(base_slots_src)

        return total_freeze_keys_set, base_slots_source_name, slots_tuple

    @staticmethod
    def _inherit_mode(
        mcls: type["EntityMeta"],
        *,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> tuple[set[str], str, tuple[str, ...]]:
        def _inherit_mode_validation() -> type:
            err_prefix = f"inherit-mode contract violation for the class {name},"
            internal_freeze_keys = (
                mcls._DERIVED_FREEZE_KEYS_ATTR,
                mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR,
                "__slots__",
            )
            provider_cls = mcls._resolve_single_provider(
                bases=bases,
                names=internal_freeze_keys,
            )
            if provider_cls is None:
                raise TypeError(
                    err_msg(
                        f"{err_prefix} no base class provides all of the required internal configs: "
                        f"({', '.join(internal_freeze_keys)}) and can serve as a provider"
                    )
                )
            provider_dict = provider_cls.__dict__
            derived_freeze_keys = provider_dict[mcls._DERIVED_FREEZE_KEYS_ATTR]
            derived_slots_source_name = provider_dict[mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR]
            slots = provider_dict["__slots__"]

            # Validate derived_freeze_keys
            if not isinstance(derived_freeze_keys, frozenset):
                raise TypeError(
                    err_msg(
                        f"{err_prefix} the provider class {provider_cls.__name__} provides an invalid '{mcls._DERIVED_FREEZE_KEYS_ATTR}', must be frozenset"
                    )
                )
            for internal_key in internal_freeze_keys:
                if internal_key not in derived_freeze_keys:
                    raise ValueError(
                        err_msg(
                            f"{err_prefix} the provider class {provider_cls.__name__} provides an incomplete '{mcls._DERIVED_FREEZE_KEYS_ATTR}', missing required frozen attribute: {internal_key}"
                        )
                    )
            mcls._identifiers_validation(
                mcls,
                names_iterable=derived_freeze_keys,
                iterable_name=mcls._DERIVED_FREEZE_KEYS_ATTR,
                provider_name=provider_cls.__name__,
                err_prefix=err_prefix,
                inherited=True,
            )

            # Validate derived_slots_source_name
            mcls._identifier_validation(
                name=derived_slots_source_name,
                err_prefix=f"{err_prefix} the provider class {provider_cls.__name__} provides an invalid '{mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR}',",
            )

            # Validate __slots__
            if not isinstance(slots, tuple):
                raise TypeError(
                    err_msg(
                        f"{err_prefix} the provider class {provider_cls.__name__} provides an invalid '__slots__', must be tuple"
                    )
                )
            mcls._identifiers_validation(
                mcls,
                names_iterable=slots,
                iterable_name="__slots__",
                provider_name=provider_cls.__name__,
                err_prefix=err_prefix,
                inherited=True,
            )

            return provider_cls

        provider_cls = _inherit_mode_validation()
        provider_dict = provider_cls.__dict__
        derived_freeze_keys: frozenset[str] = provider_dict[mcls._DERIVED_FREEZE_KEYS_ATTR]
        derived_slots_source_name: str = provider_dict[mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR]
        provider_slots: tuple[str, ...] = provider_dict["__slots__"]

        # Process freeze keys
        extra_freeze_keys: set[str] = mcls._get_extra_freeze_keys(
            mcls,
            name=name,
            namespace=namespace,
        )
        total_freeze_keys_set: set[str] = (
            derived_freeze_keys | extra_freeze_keys
        )  # Internal keys already included in derived_freeze_keys (validated already)

        # Process slots
        if derived_slots_source_name not in namespace:
            slots_tuple: tuple[str, ...] = provider_slots
        else:
            slots_src = namespace[derived_slots_source_name]
            if slots_src is not None:
                if not mcls._is_allowed_iterable(slots_src, allow_str_like=False):
                    raise TypeError(
                        err_msg(
                            f"the class {name} is invalidly defined, the base slots source attribute '{derived_slots_source_name}' must be None or a native iterable, got {type(slots_src).__name__}"
                        )
                    )
                mcls._identifiers_validation(
                    mcls,
                    names_iterable=slots_src,  # pyright: ignore[reportArgumentType]
                    iterable_name=derived_slots_source_name,
                    provider_name=name,
                    err_prefix="error,",
                    inherited=False,
                )
                slots_tuple: tuple[str, ...] = tuple(slots_src)  # pyright: ignore[reportArgumentType]
            else:
                slots_tuple: tuple[str, ...] = ()

        return total_freeze_keys_set, derived_slots_source_name, slots_tuple

    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, object], **kwargs):
        forbidden_namespace_attrs = (
            mcls.CONCRETE_ENTITY_FLAG_ATTR,
            mcls._DERIVED_FREEZE_KEYS_ATTR,
            mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR,
        )

        # 1) Check that no forbidden attributes are defined directly in the class body
        for attr in forbidden_namespace_attrs:
            if attr in namespace:
                raise TypeError(
                    err_msg(
                        f"the class {name} is invalidly defined, no class is allowed to define {attr} directly in the class body"
                    )
                )

        # 2) Determine mode and validate required configs
        has_base_freeze = mcls.BASE_FREEZE_KEYS_ATTR in namespace
        has_base_slots = mcls.BASE_SLOTS_SOURCE_NAME_ATTR in namespace

        if has_base_freeze != has_base_slots:
            raise TypeError(
                err_msg(
                    f"the class {name} is invalidly defined, must either define both or neither of the required configs: "
                    f"{mcls.BASE_FREEZE_KEYS_ATTR}, {mcls.BASE_SLOTS_SOURCE_NAME_ATTR}"
                )
            )

        # 3) Process according to mode
        if has_base_freeze and has_base_slots:
            # Baseline mode
            total_freeze_keys_set, slots_source_name, slots_tuple = mcls._baseline_mode(
                mcls,
                name=name,
                bases=bases,
                namespace=namespace,
            )
        else:
            # Inherit mode
            total_freeze_keys_set, slots_source_name, slots_tuple = mcls._inherit_mode(
                mcls,
                name=name,
                bases=bases,
                namespace=namespace,
            )

        # 4) Namespace updates
        total_freeze_keys_set.discard(
            mcls.CONCRETE_ENTITY_FLAG_ATTR
        )  # never freeze the concrete entity flag, extra safety (should not be in the set anyway)
        namespace[mcls._DERIVED_FREEZE_KEYS_ATTR] = (
            total_freeze_keys_set  # will be a frozenset[str] after stage 5 (freezing)
        )
        namespace[mcls._DERIVED_SLOTS_SOURCE_NAME_ATTR] = (
            slots_source_name  # stage 5 (freezing) keeps it str
        )
        namespace["__slots__"] = slots_tuple  # stage 5 (freezing) keeps it tuple[str]

        # 5) Freeze the attributes specified in total_freeze_keys_set that exist in the namespace
        for freeze_attr in total_freeze_keys_set:
            if freeze_attr in namespace:
                namespace[freeze_attr] = mcls._freeze(mcls, namespace[freeze_attr])

        return super().__new__(mcls, name, bases, namespace, **kwargs)

    def __setattr__(cls, name: str, value: object):
        mcls = type(cls)
        # Allow setting CONCRETE_ENTITY_FLAG only once and only to None
        if name == mcls.CONCRETE_ENTITY_FLAG_ATTR:
            if name in cls.__dict__:
                raise AttributeError(
                    err_msg(f"{cls.__name__}.{name} is write-once and cannot be reassigned")
                )
            if value is not None:
                raise AttributeError(err_msg(f"{cls.__name__}.{name} must be set to None"))

        frozen_attr_names_set = cls.__dict__.get(mcls._DERIVED_FREEZE_KEYS_ATTR, None)
        if frozen_attr_names_set is None:
            raise RuntimeError(
                f"metaclass {mcls._DERIVED_FREEZE_KEYS_ATTR} injection contract violated for class {cls.__name__}, missing frozen attributes set"
            )
        if name in frozen_attr_names_set:
            raise AttributeError(
                err_msg(f"{cls.__name__}.{name} is frozen and cannot be reassigned")
            )

        return super().__setattr__(name, value)

    def __delattr__(cls, name: str):
        mcls = type(cls)
        # Prevent deletion of CONCRETE_ENTITY_FLAG
        if name == mcls.CONCRETE_ENTITY_FLAG_ATTR:
            raise AttributeError(err_msg(f"{cls.__name__}.{name} cannot be deleted"))

        frozen_attr_names_set = cls.__dict__.get(mcls._DERIVED_FREEZE_KEYS_ATTR, None)
        if frozen_attr_names_set is None:
            raise RuntimeError(
                f"metaclass {mcls._DERIVED_FREEZE_KEYS_ATTR} injection contract violated for class {cls.__name__}, missing frozen attributes set"
            )
        if name in frozen_attr_names_set:
            raise AttributeError(err_msg(f"{cls.__name__}.{name} is frozen and cannot be deleted"))

        return super().__delattr__(name)


class BaseEntity(metaclass=EntityMeta):
    TABLE_META: TableMeta | None = None  # to be overridden in subclasses
    PRIMARY_KEYS: PrimaryKeyNames | None = None  # to be overridden in subclasses
    FOREIGN_KEYS: ForeignKeyMapping | None = None  # to be overridden in subclasses
    TABLE_NAME: TableName | None = None  # to be overridden in subclasses
    _BASE_FREEZE_KEYS: Final[tuple[str]] = (
        "TABLE_META",
        "PRIMARY_KEYS",
        "FOREIGN_KEYS",
        "TABLE_NAME",
    )

    _BASE_SLOTS_SOURCE_NAME: Final[str] = "TABLE_META"

    @classmethod
    def _validate_table_meta(cls) -> None:
        if not isinstance(cls.TABLE_META, cls.frozen_type(dict, by_type=True)):
            raise TypeError(err_msg("TABLE_META must be a dict"))
        if not cls.TABLE_META:
            raise TypeError(err_msg("TABLE_META must be a non-empty dict"))

        for f_name, f_meta in cls.TABLE_META.items():
            result = is_valid_identifier(f_name)
            if result == 1:
                raise TypeError(err_msg("TABLE_META keys must be strings"))
            elif result == 2:
                raise ValueError(err_msg("TABLE_META cannot contain empty field names"))
            elif result == 3:
                raise ValueError(err_msg(f"TABLE_META field '{f_name}' is not a valid identifier"))
            elif result == 4:
                raise ValueError(err_msg(f"TABLE_META field '{f_name}' is a Python keyword"))

            if not isinstance(f_meta, cls.frozen_type(FieldMeta, by_type=True)):
                raise TypeError(err_msg("TABLE_META values must be of type FieldMeta"))
            if not isinstance(f_meta.py_type, cls.frozen_type(type, by_type=True)):
                raise TypeError(err_msg("FieldMeta.py_type must be a type"))
            if f_meta.py_type is type(None):
                raise TypeError(err_msg("FieldMeta.py_type cannot be type(None)"))
            if not isinstance(f_meta.nullable, cls.frozen_type(bool, by_type=True)):
                raise TypeError(err_msg("FieldMeta.nullable must be a bool"))

    @classmethod
    def _validate_primary_keys(cls) -> None:
        assert cls.TABLE_META is not None
        if not isinstance(cls.PRIMARY_KEYS, cls.frozen_type(tuple, by_type=True)):
            raise TypeError(err_msg("PRIMARY_KEYS must be a tuple"))
        if not cls.PRIMARY_KEYS:
            raise TypeError(err_msg("PRIMARY_KEYS must be a non-empty tuple"))

        for pk in cls.PRIMARY_KEYS:
            if not isinstance(pk, cls.frozen_type(str, by_type=True)):
                raise TypeError(err_msg("PRIMARY_KEYS must be a tuple of strings"))
            if pk not in cls.TABLE_META:
                raise ValueError(
                    err_msg(f"PRIMARY_KEYS contains '{pk}' which is not in TABLE_META")
                )
            pk_meta: FieldMeta = cls.TABLE_META[pk]
            if pk_meta.nullable:
                raise ValueError(
                    err_msg(
                        f"PRIMARY_KEYS contains '{pk}' which is marked as nullable in TABLE_META"
                    )
                )

    @classmethod
    def _validate_foreign_keys(cls) -> None:
        assert cls.TABLE_META is not None and cls.FOREIGN_KEYS is not None
        if not isinstance(cls.FOREIGN_KEYS, cls.frozen_type(dict, by_type=True)):
            raise TypeError(err_msg("FOREIGN_KEYS must be a dict"))

        for table_name, ref_mapping in cls.FOREIGN_KEYS.items():
            if not isinstance(table_name, cls.frozen_type(str, by_type=True)):
                raise TypeError(err_msg("FOREIGN_KEYS must be a dict with table names as str keys"))
            if not table_name:
                raise ValueError(err_msg("FOREIGN_KEYS cannot contain empty table names as keys"))
            if not isinstance(ref_mapping, cls.frozen_type(dict, by_type=True)):
                raise TypeError(
                    err_msg("FOREIGN_KEYS must be of type ForeignKeyMapping with dict values")
                )
            if not ref_mapping:
                raise ValueError(
                    err_msg("FOREIGN_KEYS cannot contain empty ref_mappings as values")
                )

            for ref_col, fk_col in ref_mapping.items():
                ref_col_result = is_valid_identifier(ref_col)
                fk_col_result = is_valid_identifier(fk_col)
                if ref_col_result == 1:
                    raise TypeError(
                        err_msg(
                            "FOREIGN_KEYS ref_mappings must have str keys for referenced columns"
                        )
                    )
                elif ref_col_result == 2:
                    raise ValueError(
                        err_msg(
                            "FOREIGN_KEYS ref_mappings cannot have empty referenced column names"
                        )
                    )
                elif ref_col_result == 3:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings referenced column '{ref_col}' is not a valid identifier"
                        )
                    )
                elif ref_col_result == 4:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings referenced column '{ref_col}' is a Python keyword"
                        )
                    )

                if fk_col_result == 1:
                    raise TypeError(
                        err_msg(
                            "FOREIGN_KEYS ref_mappings must have str values for foreign key columns"
                        )
                    )
                elif fk_col_result == 2:
                    raise ValueError(
                        err_msg(
                            "FOREIGN_KEYS ref_mappings cannot have empty foreign key column names"
                        )
                    )
                elif fk_col_result == 3:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings foreign key column '{fk_col}' is not a valid identifier"
                        )
                    )
                elif fk_col_result == 4:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings foreign key column '{fk_col}' is a Python keyword"
                        )
                    )

                if fk_col not in cls.TABLE_META:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings contains foreign key column '{fk_col}' which is not in TABLE_META"
                        )
                    )

    @classmethod
    def _validate_table_name(cls) -> None:
        if not isinstance(cls.TABLE_NAME, cls.frozen_type(str, by_type=True)):
            raise TypeError(err_msg("TABLE_NAME must be a string"))

    @classmethod
    def _validate_entity_configs(cls) -> None:
        cls._validate_table_name()
        cls._validate_table_meta()
        cls._validate_primary_keys()
        cls._validate_foreign_keys()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        mcls = type(cls)
        concrete_flag = mcls.CONCRETE_ENTITY_ATTR
        if concrete_flag in cls.__dict__:
            raise TypeError(
                err_msg(
                    f"{cls.__name__} is invalidly defined, {concrete_flag} is already set.\n"
                    "Only BaseEntity may set this flag and only once.\n"
                    "Possible cause: attempting to set the flag in a subclass __init_subclass__ method before calling super().__init_subclass__()"
                )
            )

        required_config_set = set(cls._BASE_FREEZE_KEYS)
        provided_config_set = {config for config in required_config_set if config in cls.__dict__}
        if not provided_config_set:
            return  # allow intermediate abstract subclasses
        missing_configs = required_config_set - provided_config_set
        if missing_configs:
            raise TypeError(
                err_msg(
                    f"A subclass must either override all required configs or none of them. "
                    f"Got overrides for: {provided_config_set}, missing: {missing_configs}"
                )
            )

        # All required configs are provided, proceed to validate them
        cls._validate_entity_configs()
        setattr(cls, concrete_flag, None)  # mark as a flag that this is a concrete entity class

    @classmethod
    def get_pk_names(cls) -> PrimaryKeyNames:
        assert cls.PRIMARY_KEYS is not None
        return cls.PRIMARY_KEYS

    def get_pk_values(self) -> dict[FieldName, Any]:
        pk_names = self.get_pk_names()
        pk_values: dict[FieldName, Any] = {
            pk_name: self.get_field_value(pk_name) for pk_name in pk_names
        }
        return pk_values

    @classmethod
    def get_fk_mapping(cls) -> ForeignKeyMapping:
        assert cls.FOREIGN_KEYS is not None
        return cls.FOREIGN_KEYS

    @classmethod
    def get_fk_ref_mapping_for_entity(cls, entity_cls: type["BaseEntity"]) -> RefMapping:
        assert (
            isinstance(entity_cls, type)
            and issubclass(entity_cls, BaseEntity)
            and entity_cls.is_concrete_entity()
            and entity_cls.TABLE_NAME is not None
        )

        fk_mapping = cls.get_fk_mapping()
        entity_ref_mapping = fk_mapping.get(entity_cls.TABLE_NAME, None)
        if entity_ref_mapping is None:
            raise ValueError(
                err_msg(f"No foreign key relationship found to entity '{entity_cls.TABLE_NAME}'")
            )
        return entity_ref_mapping

    @classmethod
    def get_fk_name_ref_entity_col(
        cls, entity_cls: type["BaseEntity"], ref_col: FieldName
    ) -> FieldName:
        entity_ref_mapping = cls.get_fk_ref_mapping_for_entity(entity_cls)

        fk_col = entity_ref_mapping.get(ref_col, None)
        if fk_col is None:
            raise ValueError(
                err_msg(
                    f"No foreign key relationship found to entity '{entity_cls.TABLE_NAME}' "
                    f"for referenced column '{ref_col}'"
                )
            )
        return fk_col

    def get_fk_value_ref_entity_col(
        self, entity_cls: type["BaseEntity"], ref_col: FieldName
    ) -> Any:
        fk_col = self.get_fk_name_ref_entity_col(entity_cls, ref_col)
        return self.get_field_value(fk_col)

    def set_fk_value_ref_entity_col(
        self, entity_cls: type["BaseEntity"], ref_col: FieldName, new_value: Any
    ) -> None:
        fk_col = self.get_fk_name_ref_entity_col(entity_cls, ref_col)
        return self.set_field_value(fk_col, new_value)

    @classmethod
    def get_fk_name_ref_single_pk_entity(cls, entity_cls: type["SinglePkEntity"]) -> FieldName:
        assert (
            isinstance(entity_cls, type)
            and issubclass(entity_cls, SinglePkEntity)
            and entity_cls.is_concrete_entity()
        )
        ref_pk_name = entity_cls.get_pk_name()
        return cls.get_fk_name_ref_entity_col(entity_cls, ref_pk_name)

    def get_fk_value_ref_single_pk_entity(self, entity_cls: type["SinglePkEntity"]) -> Any:
        fk_col = self.get_fk_name_ref_single_pk_entity(entity_cls)
        return self.get_field_value(fk_col)

    def set_fk_value_ref_single_pk_entity(
        self, entity_cls: type["SinglePkEntity"], new_value: Any
    ) -> None:
        fk_col = self.get_fk_name_ref_single_pk_entity(entity_cls)
        return self.set_field_value(fk_col, new_value)

    def get_field_value(self, field_name: FieldName) -> Any:
        assert self.TABLE_META is not None and self.PRIMARY_KEYS is not None
        pk_set = set(self.PRIMARY_KEYS)

        if field_name not in self.TABLE_META:
            raise ValueError(err_msg(f"field '{field_name}' is not a valid field of the entity"))
        field_value = getattr(self, field_name, UNSET)
        field_meta = self.TABLE_META[field_name]

        if field_value is UNSET:
            if field_name in pk_set:
                raise ValueError(err_msg(f"primary key field '{field_name}' is not set"))
            return field_value

        if not field_meta.is_valid_value(field_value):
            allowed_types = tuple(t.__name__ for t in field_meta.allowed_types())
            if field_name in pk_set:
                raise TypeError(
                    err_msg(
                        f"primary key field '{field_name}' must be of type {allowed_types}, got {type(field_value).__name__} instead"
                    )
                )
            else:
                raise TypeError(
                    err_msg(
                        f"field '{field_name}' must be of type {allowed_types}, got {type(field_value).__name__} instead"
                    )
                )
        return field_value

    def set_field_value(self, field_name: FieldName, new_value: Any) -> None:
        assert self.TABLE_META is not None and self.PRIMARY_KEYS is not None
        pk_set = set(self.PRIMARY_KEYS)

        if field_name not in self.TABLE_META:
            raise ValueError(err_msg(f"field '{field_name}' is not a valid field of the entity"))
        field_meta = self.TABLE_META[field_name]

        if new_value is UNSET:
            if field_name in pk_set:
                raise ValueError(
                    err_msg(
                        f"primary key field '{field_name}' cannot be set to UNSET (missing value)"
                    )
                )
            setattr(self, field_name, new_value)
            return

        if not field_meta.is_valid_value(new_value):
            allowed_types = tuple(t.__name__ for t in field_meta.allowed_types())
            if field_name in pk_set:
                raise TypeError(
                    err_msg(
                        f"primary key field '{field_name}' must be of type {allowed_types}, got {type(new_value).__name__} instead"
                    )
                )
            else:
                raise TypeError(
                    err_msg(
                        f"field '{field_name}' must be of type {allowed_types}, got {type(new_value).__name__} instead"
                    )
                )
        setattr(self, field_name, new_value)

    @classmethod
    def _validate_insert_data(cls, data: dict[FieldName, Any]) -> None:
        assert cls.TABLE_META is not None
        required = {f_name for f_name, f_meta in cls.TABLE_META.items() if not f_meta.nullable}
        provided = set(data.keys())
        missing = required - provided
        if missing:
            raise ValueError(err_msg(f"missing required fields for INSERT: {missing}"))

    @classmethod
    def _filter_data(cls, data: dict[FieldName, Any]) -> dict[FieldName, Any]:
        assert isinstance(data, dict) and cls.TABLE_META is not None
        filtered_fields = {
            f_name: f_val
            for f_name, f_val in data.items()
            if f_name in cls.TABLE_META and f_val is not UNSET
        }
        return filtered_fields

    @staticmethod
    def _simulate_sql_exc(sql: str, data: dict[FieldName, Any]) -> None:
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

    @classmethod
    def is_concrete_entity(cls) -> bool:
        mcls = type(cls)
        concrete_flag_name = mcls.CONCRETE_ENTITY_ATTR
        cls_dict = cls.__dict__
        if concrete_flag_name not in cls_dict:
            return False
        concrete_flag = cls_dict[concrete_flag_name]
        if concrete_flag is not None:
            raise RuntimeError(
                err_msg(
                    f"metaclass {mcls.CONCRETE_ENTITY_ATTR} injection contract violated for class {cls.__name__}, if the concrete entity flag is present, it must be set to None"
                )
            )
        return True

    @classmethod
    def validate_concrete_entity(cls) -> None:
        if not cls.is_concrete_entity():
            raise TypeError(
                err_msg(
                    f"the class {cls.__name__} is abstract and serves as a base class only, cannot be used as a concrete entity.\n"
                    "This includes attempts to instantiate it or use any class methods that require a concrete entity class."
                )
            )

    def __new__(cls, *args, **kwargs):
        if not cls.is_concrete_entity():
            raise TypeError(
                err_msg(
                    f"Cannot instantiate a {cls.__name__} object directly, the class is abstract and serves as a base class only"
                )
            )
        return super().__new__(cls)

    @classmethod
    def validate_data(cls, data: dict[FieldName, Any]) -> None:
        assert cls.TABLE_META is not None and cls.PRIMARY_KEYS is not None
        pk_set: set[FieldName] = set(cls.PRIMARY_KEYS)

        for field_name, field_meta in cls.TABLE_META.items():
            if field_name in data:
                field_value = data[field_name]
                if not field_meta.is_valid_value(
                    field_value
                ):  # check also for type(None) for nullable fields
                    allowed_types = tuple(t.__name__ for t in field_meta.allowed_types())
                    raise TypeError(
                        err_msg(
                            f"field '{field_name}' must be of type {allowed_types}, got {type(field_value).__name__} instead"
                        )
                    )
            elif field_name in pk_set:
                raise ValueError(err_msg(f"required primary key field '{field_name}' is missing"))

    def __init__(self, data: dict[FieldName, Any]) -> None:
        data = self._filter_data(data)  # filter out UNSET fields and non-TABLE_META fields
        self.validate_data(data)
        for field_name, field_value in data.items():
            setattr(self, field_name, field_value)

    def validate_fields(self) -> dict[FieldName, Any]:
        assert self.TABLE_META is not None
        data = {
            field_name: getattr(self, field_name, UNSET) for field_name in self.TABLE_META
        }  # get current field values, default to UNSET if missing
        # filter out UNSET fields
        filtered_data = self._filter_data(data)  # type: ignore
        self.validate_data(filtered_data)
        return filtered_data

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        assert self.PRIMARY_KEYS is not None
        if not simulate and not cur:
            raise ValueError(err_msg("'cur' is required"))

        data = self.validate_fields()
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
        assert self.PRIMARY_KEYS is not None
        if not simulate and not cur:
            raise ValueError(err_msg("'cur' is required"))

        data = self.validate_fields()
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
            raise ValueError(err_msg("'cur' is required"))

        # 1) Try UPDATE (patch existing row)
        row_updated = self.update_fields_db(cur=cur, simulate=simulate)
        if row_updated:
            return

        # 2) If no row was updated, try INSERT with the provided columns
        self.insert_to_db(cur=cur, simulate=simulate, on_conflict=False)

    def exists_in_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        assert self.PRIMARY_KEYS is not None
        if not simulate and not cur:
            raise ValueError(err_msg("'cur' is required"))

        data = self.validate_fields()
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


class SinglePkEntity(BaseEntity):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        pk_names = cls.get_pk_names()
        if len(pk_names) != 1:
            raise TypeError(
                err_msg(
                    f"SinglePkEntity subclasses must have exactly one primary key, got {len(pk_names)} instead"
                )
            )

    @classmethod
    def get_pk_name(cls) -> FieldName:
        return cls.get_pk_names()[0]

    def get_pk_value(self) -> Any:
        pk_name = self.get_pk_name()
        return self.get_field_value(pk_name)

    def set_pk_value(self, pk_value: Any) -> None:
        pk_name = self.get_pk_name()
        self.set_field_value(pk_name, pk_value)


class DependentEntity(BaseEntity):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        fk_mapping = cls.get_fk_mapping()
        if len(fk_mapping) != 1:
            raise TypeError(
                err_msg(
                    f"DependentEntity subclasses must have a foreign key relationship with exactly one table, got {len(fk_mapping)} instead"
                )
            )
        # BaseEntity guarantees that fk_ref_mapping is non-empty
        fk_ref_mapping = next(iter(fk_mapping.values()))

        fk_set = set(fk_ref_mapping.values())  # BaseEntity guarantees that it's a non-empty set
        pk_set = set(cls.get_pk_names())
        if not fk_set.issubset(pk_set):
            raise TypeError(
                err_msg(
                    "DependentEntity subclasses' foreign key columns must be a subset of their primary keys"
                )
            )

    @classmethod
    def get_fk_ref_mapping(cls) -> RefMapping:
        fk_mapping = cls.get_fk_mapping()

        # type checker safety (should not happen due to __init_subclass__ check)
        if len(fk_mapping) != 1:
            raise RuntimeError(
                err_msg(
                    f"metaclass DependentEntity foreign key relationship contract violated for class {cls.__name__}, expected exactly one foreign key relationship"
                )
            )
        entity_ref_mapping = next(iter(fk_mapping.values()))
        return entity_ref_mapping

    @classmethod
    def get_fk_name_ref_col(cls, ref_col: FieldName) -> FieldName:
        entity_ref_mapping = cls.get_fk_ref_mapping()

        fk_col = entity_ref_mapping.get(ref_col, None)
        if fk_col is None:
            raise ValueError(
                err_msg(f"No foreign key relationship found for referenced column '{ref_col}'")
            )
        return fk_col

    def get_fk_value_ref_col(self, ref_col: FieldName) -> Any:
        fk_col = self.get_fk_name_ref_col(ref_col)
        return self.get_field_value(fk_col)

    def set_fk_value_ref_col(self, ref_col: FieldName, new_value: Any) -> None:
        fk_col = self.get_fk_name_ref_col(ref_col)
        return self.set_field_value(fk_col, new_value)


class DependentRowEntity(DependentEntity):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        # DependentEntity __init_subclass__ already checks that there's exactly one foreign key relationship
        # it also guarantees that the local fk column names are all part of the primary key

        fk_mapping = cls.get_fk_mapping()
        # BaseEntity guarantees that fk_ref_mapping is non-empty
        fk_ref_mapping = next(iter(fk_mapping.values()))

        fk_set = set(fk_ref_mapping.values())  # BaseEntity guarantees that it's a non-empty set
        pk_set = set(cls.get_pk_names())

        # checking if fk_set == pk_set is equivalent, because fk_set is guaranteed to be a subset of pk_set
        # (it's a faster check this way)
        if len(fk_set) == len(pk_set):
            raise TypeError(
                err_msg(
                    "DependentRowEntity subclasses' foreign key columns must be a proper subset of their primary keys"
                )
            )


class ExtensionEntity(DependentEntity):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        # DependentEntity __init_subclass__ already checks that there's exactly one foreign key relationship
        # it also guarantees that the local fk column names are all part of the primary key

        fk_mapping = cls.get_fk_mapping()
        # BaseEntity guarantees that fk_ref_mapping is non-empty
        fk_ref_mapping = next(iter(fk_mapping.values()))

        fk_set = set(fk_ref_mapping.values())  # BaseEntity guarantees that it's a non-empty set
        pk_set = set(cls.get_pk_names())

        # checking if fk_set != pk_set is equivalent, because fk_set is guaranteed to be a subset of pk_set
        # (it's a faster check this way)
        # doing if len(fk_set) != len(pk_set) is equivalent but less clear
        if len(fk_set) < len(pk_set):
            raise TypeError(
                err_msg(
                    "ExtensionEntity subclasses' foreign key columns must exactly match their primary keys"
                )
            )


class BinaryAssociationEntity(BaseEntity):
    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        super().insert_to_db(cur=cur, simulate=simulate, on_conflict=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.is_concrete_entity():
            return

        pk_names = cls.get_pk_names()
        fk_mapping = cls.get_fk_mapping()

        if len(pk_names) != 2:
            raise TypeError(
                err_msg(
                    f"BinaryAssociationEntity subclasses must have exactly two primary keys, got {len(pk_names)} instead"
                )
            )
        if len(fk_mapping) != 2:
            raise TypeError(
                err_msg(
                    f"BinaryAssociationEntity subclasses must have exactly two foreign key relationships, got {len(fk_mapping)} instead"
                )
            )
        if not all(len(ref_mapping) == 1 for ref_mapping in fk_mapping.values()):
            raise TypeError(
                err_msg(
                    "BinaryAssociationEntity subclasses must have exactly one foreign key column per foreign key relationship"
                )
            )
        pk_set = set(pk_names)
        fk_set = {fk_col for ref_mapping in fk_mapping.values() for fk_col in ref_mapping.values()}
        if pk_set != fk_set:
            raise TypeError(
                err_msg(
                    "BinaryAssociationEntity subclasses' primary keys must exactly match their foreign key columns"
                )
            )

    def update_fields_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> bool:
        raise NotImplementedError(
            err_msg(
                "this method is not implemented. "
                "Use insert_to_db instead, as binary association entities are immutable."
            )
        )

    def upsert_to_db(self, cur: sqlite3.Cursor, simulate: bool = False) -> None:
        raise NotImplementedError(
            err_msg(
                "this method is not implemented. "
                "Use insert_to_db instead, as binary association entities are immutable."
            )
        )
