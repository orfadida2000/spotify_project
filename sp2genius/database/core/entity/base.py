import inspect
import sqlite3
from collections.abc import ItemsView, Iterable, KeysView, Mapping, ValuesView
from textwrap import dedent
from types import MappingProxyType
from typing import Any, Final

from sp2genius.utils.builtins import BuiltinAnalysis
from sp2genius.utils.class_introspection import (
    C3MergeError,
    MROError,
    class_instances_have_dict,
    class_instances_support_weakref,
    compute_mro,
)
from sp2genius.utils.errors import err_msg
from sp2genius.utils.identifier import is_valid_py_identifier

from ..typing import (
    UNSET,
    FieldMeta,
    FieldName,
    ForeignKeyMapping,
    PrimaryKeyNames,
    RefMapping,
    TableMeta,
    TableName,
)


class EntityMeta(type):
    # Static attribute name for concrete entity flag
    CONCRETE_ENTITY_FLAG_ATTR: Final[str] = "_CONCRETE_ENTITY"

    # class-body baseline knobs (both-or-none)
    BASE_FREEZE_KEYS_ATTR: Final[str] = "_BASE_FREEZE_KEYS"  # iterable[str]
    BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR: Final[str] = (
        "_BASE_EXTRA_SLOTS_SOURCE_NAME"  # str (e.g. "SCHEMA_META")
    )

    # class-body extension knob (optional)
    EXTRA_FREEZE_KEYS_ATTR: Final[str] = "_EXTRA_FREEZE_KEYS"  # iterable[str]

    # metaclass-injected internal attrs (must not appear in class body)
    _DERIVED_FREEZE_KEYS_ATTR: Final[str] = "_DERIVED_FREEZE_KEYS"  # frozenset[str]
    _DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR: Final[str] = "_DERIVED_EXTRA_SLOTS_SOURCE_NAME"  # str
    _DERIVED_SLOTS_MAP_ATTR: Final[str] = "_DERIVED_SLOTS_MAP"  # dict[str, type]

    # metaclass-level registry of all entity classes it created
    _REGISTERED_ENTITY_CLASSES: Final[set[type["EntityMeta"]]] = set()

    _BUILTIN_ANALYSIS: Final[BuiltinAnalysis] = BuiltinAnalysis()

    @staticmethod
    def _get_internal_use_keyset(mcls: type["EntityMeta"]) -> set[str]:
        """
        internal_use_keys_set: set[str] = {
            mcls._DERIVED_FREEZE_KEYS_ATTR,
            mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR,
            mcls._DERIVED_SLOTS_MAP_ATTR,
        }
        """
        internal_use_keys_set: set[str] = {
            mcls._DERIVED_FREEZE_KEYS_ATTR,
            mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR,
            mcls._DERIVED_SLOTS_MAP_ATTR,
        }
        return internal_use_keys_set

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
            allow_dunder=False,
        )
        return set(extra_freeze_keys)  # pyright: ignore[reportArgumentType]

    @staticmethod
    def _resolve_single_registered_provider(
        mcls: type["EntityMeta"],
        *,
        cls_mro: tuple[type, ...],
        attribute_names: tuple[str, ...],
    ) -> tuple[type | None, set[str]]:
        """
        It goes over the mro and stops at the first registered base class (in metaclass registry), this base class should provide all required configs in its __dict__.
        If such a class is found, it checks what required configs are not provided by it.

        Args:
            mcls: The metaclass.
            cls_mro: The MRO of the class being created (without the class itself).
            attribute_names: The names of the required attributes to look for in the provider class.

        Returns:
            registered_baseclass (type | None): The first registered base class that was found in the mro order or None if no such class was found.
            missing_attributes (set[str]): A set of attribute names that were not provided by the found registered base class, if no registered base class was found, this set contains all attribute names.
        """

        # This is part of inherit-mode resolution which means we already inspected the namespace of the actual class being created
        # and it was determined that it can not serve as a provider.
        registered_baseclass: type | None = None
        missing_attributes: set[str] = set(attribute_names)
        for baseclass in cls_mro:
            if baseclass in mcls._REGISTERED_ENTITY_CLASSES:
                registered_baseclass = baseclass
                break

        registered_baseclass_dict = (
            registered_baseclass.__dict__ if registered_baseclass is not None else {}
        )
        for attr_name in attribute_names:
            if attr_name in registered_baseclass_dict:
                missing_attributes.discard(attr_name)

        return registered_baseclass, missing_attributes

    @staticmethod
    def _freeze(mcls: type["EntityMeta"], obj: object) -> Any:
        def is_valid_freeze_method(fn: Any) -> tuple[bool, str]:
            if not callable(fn):
                return False, "not callable"
            try:
                sig = inspect.signature(fn)
            except (TypeError, ValueError):
                return False, "could not retrieve signature"

            params = list(sig.parameters.values())

            # Must be exactly one parameter
            if len(params) != 1:
                return False, f"expected exactly one parameter, found {len(params)}"

            p = params[0]

            # Must be keyword-only
            if p.kind is not inspect.Parameter.KEYWORD_ONLY:
                return False, f"expected keyword-only parameter, found kind: {p.kind!r}"

            # Must be named "freezer"
            if p.name != "freezer":
                return False, f"expected parameter name 'freezer', found {p.name!r}"

            # Must be required
            if p.default is not inspect.Parameter.empty:
                return False, f"expected required parameter, found default value: {p.default!r}"

            return True, ""

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

        if isinstance(obj, (bytearray, memoryview)):
            return bytes(obj)

        freeze_attr: Any = None
        found_attr: bool = False
        try:
            freeze_attr = getattr(obj, "_freeze")  # noqa: B009
            found_attr = True
        except AttributeError:
            pass

        if not found_attr:
            return obj

        is_valid, reason = is_valid_freeze_method(freeze_attr)
        if not is_valid:
            raise TypeError(
                err_msg(
                    f"contract violation: _freeze method invalidly defined on object of type {type(obj).__name__}: {reason}"
                )
            )
        return obj._freeze(freezer=lambda x: mcls._freeze(mcls, x))  # pyright: ignore[reportAttributeAccessIssue]

    @staticmethod
    def frozen_type(obj: Any, by_type: bool = False) -> type:  # noqa: N804
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


        Args:
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
        allow_dunder: bool = False,
    ) -> None:
        err_prefix = err_prefix.strip()
        if not err_prefix:
            err_prefix = "error,"

        is_identifier = is_valid_py_identifier(name)
        if is_identifier == 1:
            raise TypeError(err_msg(f"{err_prefix} non-str name of type {type(name).__name__}"))
        elif is_identifier == 2:
            raise ValueError(err_msg(f"{err_prefix} empty string name"))
        elif is_identifier == 3:
            raise ValueError(err_msg(f"{err_prefix} invalid python identifier {name!r}"))
        elif is_identifier == 4:
            raise ValueError(err_msg(f"{err_prefix} python keyword {name!r}"))
        elif is_identifier == 5:
            if not allow_dunder:
                raise ValueError(err_msg(f"{err_prefix} dunder identifier {name!r}"))

    @staticmethod
    def _identifiers_validation(
        mcls: type["EntityMeta"],
        *,
        names_iterable: Iterable[object],
        iterable_name: str,
        provider_name: str,
        err_prefix: str = "",
        inherited: bool = False,
        allow_dunder: bool = False,
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
                allow_dunder=allow_dunder,
            )

    @staticmethod
    def _normalized_slots_validation(
        mcls: type["EntityMeta"],
        *,
        slots: Iterable[object],
        cls_name: str,
    ) -> None:
        def _slot_validation(
            *,
            name: object,
            err_prefix: str,
        ) -> None:
            if name in {"__dict__", "__weakref__"}:
                return  # special slot names are allowed
            mcls._identifier_validation(
                name=name,
                err_prefix=err_prefix,
                allow_dunder=False,
            )

        base_err = f"contract violation error: the class {cls_name} defines an invalid '__slots__', it contains"

        for slot in slots:
            _slot_validation(
                name=slot,
                err_prefix=base_err,
            )

    @staticmethod
    def _slots_normalization_validation(
        mcls: type["EntityMeta"],
        slots: object,
        cls_name: str,
    ) -> tuple[str, ...] | dict[str, Any]:
        if slots is None:
            raise TypeError(
                f"the class {cls_name} defines an invalid '__slots__', it cannot be None"
            )
        if not isinstance(slots, Iterable):
            raise TypeError(
                f"the class {cls_name} defines an invalid '__slots__', expected an iterable, got {type(slots).__name__}"
            )
        if isinstance(slots, str):
            norm_slots = (slots,)
        elif isinstance(slots, Mapping):
            norm_slots = dict(slots)
        else:
            norm_slots = tuple(slots)
        mcls._normalized_slots_validation(
            mcls,
            slots=iter(norm_slots),
            cls_name=cls_name,
        )
        return norm_slots

    @staticmethod
    def _baseline_meta_mode(
        mcls: type["EntityMeta"],
        *,
        name: str,
        cls_mro: tuple[type, ...],
        namespace: dict[str, object],
    ) -> tuple[set[str], str, set[str]]:
        def _baseline_meta_mode_validation() -> None:
            """
            Validate that the required configs are well defined in the class namespace.
            It is assumed that the required configs presence has already been checked.
            """
            err_prefix = f"baseline-meta-mode contract violation for the class {name},"
            base_freeze_keys = namespace[mcls.BASE_FREEZE_KEYS_ATTR]
            base_extra_slots_source_name = namespace[mcls.BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR]

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

            # Validate base_extra_slots_source_name
            mcls._identifier_validation(
                name=base_extra_slots_source_name,
                err_prefix=f"{err_prefix} the class {name} defines an invalid '{mcls.BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR}',",
            )
            assert isinstance(base_extra_slots_source_name, str), (
                "static analysis hint (_identifier_validation always raises if not str)"
            )

            # Validate base_extra_slots_source_name namespace value. If present, it must be either None or a native iterable,
            # if not present, it will be treated as None (no extra slots)
            if (
                base_extra_slots_src := namespace.get(base_extra_slots_source_name, None)
            ) is not None:
                if not mcls._is_allowed_iterable(base_extra_slots_src, allow_str_like=False):
                    raise TypeError(
                        err_msg(
                            f"{err_prefix} the class {name} is invalidly defined, the base extra slots source attribute {base_extra_slots_source_name!r} must be None or a native iterable, got {type(base_extra_slots_src).__name__}"
                        )
                    )
                mcls._identifiers_validation(
                    mcls,
                    names_iterable=base_extra_slots_src,  # pyright: ignore[reportArgumentType]
                    iterable_name=base_extra_slots_source_name,
                    provider_name=name,
                    err_prefix=err_prefix,
                    inherited=False,
                )

        _baseline_meta_mode_validation()

        # ------ Process slots ------
        # must be present in namespace (otherwise baseline mode function wouldn't been called) and already validated (see _baseline_meta_mode_validation)
        base_extra_slots_source_name: str = namespace[mcls.BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR]
        # if present in namespace, must be either None or a native iterable (validated above, see _baseline_meta_mode_validation), missing as well as None means no extra slots on top of native slots (__slots__)
        extra_slots_set: set[str] = (
            set(namespace[base_extra_slots_source_name])  # pyright: ignore[reportArgumentType]
            if namespace.get(base_extra_slots_source_name, None) is not None
            else set()
        )
        # if present in namespace, must be a native iterable (validated before calling either _meta_mode function, see section 2.5 in __new__), also normalized to either tuple[str, ...] or dict[str, Any]
        native_slots_set: set[str] = (
            set() if "__slots__" not in namespace else set(namespace["__slots__"])  # pyright: ignore[reportArgumentType]
        )  # pyright: ignore[reportArgumentType]
        total_slots_set: set[str] = extra_slots_set | native_slots_set

        # ------ Process freeze keys ------
        # must be present in namespace (otherwise baseline mode function wouldn't been called) and already validated (see _baseline_meta_mode_validation)
        base_freeze_keys: Iterable[str] = namespace[mcls.BASE_FREEZE_KEYS_ATTR]
        base_freeze_keys_set: set[str] = set(base_freeze_keys)
        # optionally present in namespace, if present then already validated by _get_extra_freeze_keys and normalized into a set, else returned as an empty set
        extra_freeze_keys_set: set[str] = mcls._get_extra_freeze_keys(
            mcls,
            name=name,
            namespace=namespace,
        )
        # attributes reserved for internal use by the metaclass, always frozen
        internal_use_keys_set: set[str] = mcls._get_internal_use_keyset(mcls)
        total_freeze_keys_set: set[str] = (
            base_freeze_keys_set | extra_freeze_keys_set | internal_use_keys_set
        )

        return total_freeze_keys_set, base_extra_slots_source_name, total_slots_set

    @staticmethod
    def _inherit_meta_mode(
        mcls: type["EntityMeta"],
        *,
        name: str,
        cls_mro: tuple[type, ...],
        namespace: dict[str, object],
    ) -> tuple[set[str], str, set[str]]:
        def _inherit_meta_mode_validation() -> type:
            """
            Validate that the required configs are well defined in a base class registered in the metaclass registry.

            Returns:
                provider_cls (type): The registered base class that provides all of the required configs.
            """
            err_prefix = f"inherit-meta-mode contract violation for the class {name},"
            provider_internal_attrs = (
                mcls._DERIVED_FREEZE_KEYS_ATTR,
                mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR,
            )
            registered_cls, missing_attrs = mcls._resolve_single_registered_provider(
                mcls,
                cls_mro=cls_mro,
                attribute_names=provider_internal_attrs,
            )
            if registered_cls is None:
                raise TypeError(
                    err_msg(
                        f"{err_prefix} no registered base class found in the MRO of the class {name} but baseline-meta-mode required configs are not defined in the class body"
                    )
                )
            if missing_attrs:
                raise TypeError(
                    err_msg(
                        f"{err_prefix} all required configs must be provided by the every registered base class in the MRO, "
                        f"but the first registered base class in the MRO, {registered_cls.__name__}, is missing the following required configs: {tuple(missing_attrs)!r}"
                    )
                )
            provider_dict = registered_cls.__dict__

            derived_freeze_keys = provider_dict[mcls._DERIVED_FREEZE_KEYS_ATTR]
            derived_extra_slots_source_name = provider_dict[
                mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR
            ]

            # Validate derived_freeze_keys
            if not isinstance(derived_freeze_keys, frozenset):
                raise TypeError(
                    err_msg(
                        f"{err_prefix} the provider class {provider_cls.__name__} provides an invalid {mcls._DERIVED_FREEZE_KEYS_ATTR!r}, expected frozenset, got {type(derived_freeze_keys).__name__}"
                    )
                )
            for internal_key in mcls._get_internal_use_keyset(mcls):
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

            # Validate derived_extra_slots_source_name
            mcls._identifier_validation(
                name=derived_extra_slots_source_name,
                err_prefix=f"{err_prefix} the provider class {provider_cls.__name__} provides an invalid '{mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR}',",
            )
            assert isinstance(derived_extra_slots_source_name, str), (
                "static analysis hint (_identifier_validation always raises if not str)"
            )

            # Validate derived_extra_slots_source_name namespace value. If present, it must be either None or a native iterable,
            # if not present, it will be treated as None (no extra slots)
            if (
                derived_extra_slots_src := namespace.get(derived_extra_slots_source_name, None)
            ) is not None:
                if not mcls._is_allowed_iterable(derived_extra_slots_src, allow_str_like=False):
                    raise TypeError(
                        err_msg(
                            f"{err_prefix} the class {name} is invalidly defined, the derived extra slots source attribute {derived_extra_slots_source_name!r} must be None or a native iterable, got {type(derived_extra_slots_src).__name__}"
                        )
                    )
                mcls._identifiers_validation(
                    mcls,
                    names_iterable=derived_extra_slots_src,  # pyright: ignore[reportArgumentType]
                    iterable_name=derived_extra_slots_source_name,
                    provider_name=name,
                    err_prefix=err_prefix,
                    inherited=False,
                )

            return provider_cls

        # Perform validation and get provider class
        provider_cls = _inherit_meta_mode_validation()
        provider_dict = provider_cls.__dict__

        # ------ Process slots ------
        # must be present in provider class __dict__ (part of provider baseclass validation) and already validated (see _inherit_meta_mode_validation)
        derived_extra_slots_source_name: str = provider_dict[
            mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR
        ]
        # if present in namespace, must be either None or a native iterable (validated above, see _inherit_meta_mode_validation), missing as well as None means no extra slots on top of native slots (__slots__)
        extra_slots_set: set[str] = (
            set(namespace[derived_extra_slots_source_name])  # pyright: ignore[reportArgumentType]
            if namespace.get(derived_extra_slots_source_name, None) is not None
            else set()
        )
        # if present in namespace, must be a native iterable (validated before calling either _meta_mode function, see section 2.5 in __new__), also normalized to either tuple[str, ...] or dict[str, Any]
        native_slots_set: set[str] = (
            set() if "__slots__" not in namespace else set(namespace["__slots__"])  # pyright: ignore[reportArgumentType]
        )  # pyright: ignore[reportArgumentType]
        total_slots_set: set[str] = extra_slots_set | native_slots_set

        # ------ Process freeze keys ------
        # must be present in provider class __dict__ (part of provider baseclass validation) and already validated (see _inherit_meta_mode_validation)
        derived_freeze_keys_set: frozenset[str] = provider_dict[mcls._DERIVED_FREEZE_KEYS_ATTR]
        # optionally present in namespace, if present then already validated by _get_extra_freeze_keys and normalized into a set, else returned as an empty set
        extra_freeze_keys: set[str] = mcls._get_extra_freeze_keys(
            mcls,
            name=name,
            namespace=namespace,
        )
        # attributes reserved for internal use by the metaclass, always frozen.
        # These are already included in derived_freeze_keys (validated already, see _inherit_meta_mode_validation) but as a safety measure we'll also combine them again here.
        internal_use_keys_set: set[str] = mcls._get_internal_use_keyset(mcls)
        total_freeze_keys_set: set[str] = (
            derived_freeze_keys_set | extra_freeze_keys | internal_use_keys_set
        )

        return total_freeze_keys_set, derived_extra_slots_source_name, total_slots_set

    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, object], **kwargs):
        forbidden_namespace_attrs: set[str] = mcls._get_internal_use_keyset(mcls)
        forbidden_namespace_attrs.add(mcls.CONCRETE_ENTITY_FLAG_ATTR)
        # 0) Check that no forbidden attributes are defined directly in the class body
        for attr in forbidden_namespace_attrs:
            if attr in namespace:
                raise TypeError(
                    err_msg(
                        f"the class {name!r} is invalidly defined, no class is allowed to define {attr!r} directly in the class body"
                    )
                )

        # 0.5) Check that no non-subclassable built-in types are used as bases.
        bases_set = set(bases)
        non_subclassable_builtins = mcls._BUILTIN_ANALYSIS.get_non_subclassable_builtins()
        invalid_bases = bases_set & non_subclassable_builtins
        if invalid_bases:
            invalid_bases_names = tuple(cls.__name__ for cls in invalid_bases)
            raise TypeError(
                err_msg(
                    f"the class {name!r} is invalidly defined, it uses the following non-subclassable built-in types as bases: {invalid_bases_names!r}"
                )
            )

        # 1) Pre-compute MRO based on bases only, also validates that the given bases can produce a valid MRO,
        # if the bases can not produce a valid MRO a MROError exception will be raised.
        try:
            cls_mro = compute_mro(cls=None, bases=bases)
        except C3MergeError as e:
            rem_cls_seqs: list[list[type]] = e.rem_seqs
            rem_cls_seqs_str = "\n".join(
                f"{[cls.__name__ for cls in seq]!r}" for seq in rem_cls_seqs
            )
            error_msg = dedent(
                f"""
                metaclass MRO computation error for the class {name!r}, cannot compute a valid MRO from the given bases due to C3 linearization conflict.
                The remaining class sequences that could not be merged are:
                {rem_cls_seqs_str}
                """
            )
            raise MROError(error_msg) from e

        # 2) Determine mode and validate required configs
        has_base_freeze = mcls.BASE_FREEZE_KEYS_ATTR in namespace
        has_base_slots = mcls.BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR in namespace

        if has_base_freeze != has_base_slots:
            raise TypeError(
                err_msg(
                    f"the class {name!r} is invalidly defined, must either define both or neither of the required configs: "
                    f"{mcls.BASE_FREEZE_KEYS_ATTR!r}, {mcls.BASE_EXTRA_SLOTS_SOURCE_NAME_ATTR!r}"
                )
            )

        # 2.5) Validate __slots__ if defined (should be done regardless of mode)
        if "__slots__" in namespace:
            slots = mcls._slots_normalization_validation(
                mcls,
                slots=namespace["__slots__"],
                cls_name=name,
            )
            namespace["__slots__"] = slots  # update normalized slots in namespace

        # 3) Process according to mode
        if has_base_freeze and has_base_slots:
            # Baseline mode
            total_freeze_keys_set, derived_slots_source_name, total_slot_set = (
                mcls._baseline_meta_mode(
                    mcls,
                    name=name,
                    cls_mro=cls_mro,
                    namespace=namespace,
                )
            )
        else:
            # Inherit mode
            total_freeze_keys_set, derived_slots_source_name, total_slot_set = (
                mcls._inherit_meta_mode(
                    mcls,
                    name=name,
                    cls_mro=cls_mro,
                    namespace=namespace,
                )
            )

        # 4) validate that if the class being created defines '__dict__' as a slot (via __slots__ or via the extra slots source),
        # then instances of direct parents must not have a '__dict__' attribute (using __dictoffset__).
        # In addition, if the class being created defines '__dict__' as a slot, then none of its direct parents is a subclass of a builtin type that
        # does not allow its subclasses to define '__dict__' as a slot name.
        if "__dict__" in total_slot_set:
            non_dict_slot_builtins = mcls._BUILTIN_ANALYSIS.get_builtins_disallowing_dict_slots()
            for direct_base in bases:
                if class_instances_have_dict(direct_base):
                    raise TypeError(
                        err_msg(
                            f"the class {name!r} is invalidly defined, it defines '__dict__' as a slot but its direct base class {direct_base.__name__!r} create instances with the __dict__ attribute"
                        )
                    )
                for builtin_cls in non_dict_slot_builtins:
                    if issubclass(direct_base, builtin_cls):
                        raise TypeError(
                            err_msg(
                                f"the class {name!r} is invalidly defined, it defines '__dict__' as a slot but its direct base class {direct_base.__name__!r} is a subclass of the built-in type {builtin_cls.__name__!r} which does not allow its subclasses to define '__dict__' as a slot name"
                            )
                        )

        # 5) validate that if the class being created defines '__weakref__' as a slot (via __slots__ or via the extra slots source),
        # then instances of direct parents must not support weak references (using __weakrefoffset__).
        # In addition, if the class being created defines '__weakref__' as a slot, then none of its direct parents is a subclass of a builtin type that
        # does not allow its subclasses to define '__weakref__' as a slot name.
        if "__weakref__" in total_slot_set:
            non_weakref_slot_builtins = mcls._BUILTIN_ANALYSIS.get_builtins_disallowing_weakref_slots()
            for direct_base in bases:
                if class_instances_support_weakref(direct_base):
                    raise TypeError(
                        err_msg(
                            f"the class {name!r} is invalidly defined, it defines '__weakref__' as a slot but its direct base class {direct_base.__name__!r} create instances that support weak references"
                        )
                    )
                for builtin_cls in non_weakref_slot_builtins:
                    if issubclass(direct_base, builtin_cls):
                        raise TypeError(
                            err_msg(
                                f"the class {name!r} is invalidly defined, it defines '__weakref__' as a slot but its direct base class {direct_base.__name__!r} is a subclass of the built-in type {builtin_cls.__name__!r} which does not allow its subclasses to define '__weakref__' as a slot name"
                            )
                        )
        
        # 6) compute the derived slots map,
        # if there is no base class that its slot map contains any of the other bases' slot maps, then an error is raised (python also raises in such case).
        # The computed slots map and its validation is using only registered direct bases (in the metaclass registry),
        # so passing the validation means that no conflicts exist among the registered direct bases (they can be safely merged) but conflicts may still exist with unregistered bases which there is no way to check reliably.
        derived_slots_map: dict[str, type["EntityMeta"]] = {}
        direct_bases_slot_maps: list[dict[str, type["EntityMeta"]]] = []
        for direct_base in bases:
            if direct_base in mcls._

        
        # if the class being created defines a slot (via __slots__ or via the extra slots source) which is already defined in the slot map of containing base class,
        # then an error is raised (technically allowed by python but discouraged).
        
        # 7) Namespace updates
        total_freeze_keys_set.discard(
            mcls.CONCRETE_ENTITY_FLAG_ATTR
        )  # never freeze the concrete entity flag, extra safety (should not be in the set anyway)
        namespace[mcls._DERIVED_FREEZE_KEYS_ATTR] = (
            total_freeze_keys_set  # will be a frozenset[str] after stage 5 (freezing)
        )
        namespace[mcls._DERIVED_EXTRA_SLOTS_SOURCE_NAME_ATTR] = (
            derived_slots_source_name  # stage 5 (freezing) keeps it str
        )
        namespace["__slots__"] = total_slot_set  # stage 5 (freezing) keeps it tuple[str]

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
    def get_table_name(cls) -> TableName:
        assert cls.TABLE_NAME is not None
        return cls.TABLE_NAME

    @classmethod
    def get_table_meta(cls) -> TableMeta:
        assert cls.TABLE_META is not None
        return cls.TABLE_META

    @classmethod
    def _validate_table_meta(cls) -> None:
        table_meta = cls.get_table_meta()
        if not isinstance(table_meta, cls.frozen_type(dict, by_type=True)):
            raise TypeError(err_msg("TABLE_META must be a dict"))
        if not table_meta:
            raise TypeError(err_msg("TABLE_META must be a non-empty dict"))

        for f_name, f_meta in table_meta.items():
            result = is_valid_py_identifier(f_name)
            if result == 1:
                raise TypeError(err_msg("TABLE_META keys must be strings"))
            elif result == 2:
                raise ValueError(err_msg("TABLE_META cannot contain empty field names"))
            elif result == 3:
                raise ValueError(err_msg(f"TABLE_META field {f_name!r} is not a valid identifier"))
            elif result == 4:
                raise ValueError(err_msg(f"TABLE_META field {f_name!r} is a Python keyword"))
            elif result == 5:
                raise ValueError(err_msg(f"TABLE_META field {f_name!r} is a dunder identifier"))

            if not isinstance(f_meta, cls.frozen_type(FieldMeta, by_type=True)):
                raise TypeError(err_msg("TABLE_META values must be of type FieldMeta"))

    @classmethod
    def _validate_primary_keys(cls) -> None:
        pk_names = cls.get_pk_names()
        table_meta = cls.get_table_meta()
        if not isinstance(pk_names, cls.frozen_type(tuple, by_type=True)):
            raise TypeError(err_msg("PRIMARY_KEYS must be a tuple"))
        if not pk_names:
            raise TypeError(err_msg("PRIMARY_KEYS must be a non-empty tuple"))

        for pk in pk_names:
            if not isinstance(pk, cls.frozen_type(str, by_type=True)):
                raise TypeError(err_msg("PRIMARY_KEYS must be a tuple of strings"))
            if pk not in table_meta:
                raise ValueError(
                    err_msg(f"PRIMARY_KEYS contains '{pk}' which is not in TABLE_META")
                )
            pk_meta: FieldMeta = table_meta[pk]
            if pk_meta.nullable:
                raise ValueError(
                    err_msg(
                        f"PRIMARY_KEYS contains '{pk}' which is marked as nullable in TABLE_META"
                    )
                )

    @classmethod
    def _validate_foreign_keys(cls) -> None:
        fk_mapping = cls.get_fk_mapping()
        table_meta = cls.get_table_meta()
        if not isinstance(fk_mapping, cls.frozen_type(dict, by_type=True)):
            raise TypeError(err_msg("FOREIGN_KEYS must be a dict"))

        for table_name, ref_mapping in fk_mapping.items():
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
                ref_col_result = is_valid_py_identifier(ref_col)
                fk_col_result = is_valid_py_identifier(fk_col)
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
                            f"FOREIGN_KEYS ref_mappings referenced column {ref_col!r} is not a valid identifier"
                        )
                    )
                elif ref_col_result == 4:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings referenced column {ref_col!r} is a Python keyword"
                        )
                    )
                elif ref_col_result == 5:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings referenced column {ref_col!r} is a dunder identifier"
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
                            f"FOREIGN_KEYS ref_mappings foreign key column {fk_col!r} is not a valid identifier"
                        )
                    )
                elif fk_col_result == 4:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings foreign key column {fk_col!r} is a Python keyword"
                        )
                    )
                elif fk_col_result == 5:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings foreign key column {fk_col!r} is a dunder identifier"
                        )
                    )

                if fk_col not in table_meta:
                    raise ValueError(
                        err_msg(
                            f"FOREIGN_KEYS ref_mappings contains foreign key column {fk_col!r} which is not in TABLE_META"
                        )
                    )

    @classmethod
    def _validate_table_name(cls) -> None:
        if not isinstance(cls.get_table_name(), cls.frozen_type(str, by_type=True)):
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
            and entity_cls.get_table_name() is not None
        )

        fk_mapping = cls.get_fk_mapping()
        entity_ref_mapping = fk_mapping.get(entity_cls.get_table_name(), None)
        if entity_ref_mapping is None:
            raise ValueError(
                err_msg(
                    f"No foreign key relationship found to entity '{entity_cls.get_table_name()}'"
                )
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
                    f"No foreign key relationship found to entity '{entity_cls.get_table_name()}' "
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
        pk_set = set(self.get_pk_names())
        table_meta = self.get_table_meta()

        if field_name not in table_meta:
            raise ValueError(err_msg(f"field '{field_name}' is not a valid field of the entity"))
        field_value = getattr(self, field_name, UNSET)
        field_meta = table_meta[field_name]

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
        pk_set = set(self.get_pk_names())
        table_meta = self.get_table_meta()

        if field_name not in table_meta:
            raise ValueError(err_msg(f"field '{field_name}' is not a valid field of the entity"))
        field_meta = table_meta[field_name]

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
    def get_field_type(cls, field_name: FieldName) -> type:
        table_meta = cls.get_table_meta()

        if field_name not in table_meta:
            raise ValueError(err_msg(f"field '{field_name}' is not a valid field of the entity"))

        field_meta = table_meta[field_name]
        return field_meta.get_py_type()

    @classmethod
    def _validate_insert_data(cls, data: dict[FieldName, Any]) -> None:
        table_meta = cls.get_table_meta()
        required = {f_name for f_name, f_meta in table_meta.items() if not f_meta.nullable}
        provided = set(data.keys())
        missing = required - provided
        if missing:
            raise ValueError(err_msg(f"missing required fields for INSERT: {missing}"))

    @classmethod
    def _filter_data(cls, data: dict[FieldName, Any]) -> dict[FieldName, Any]:
        assert isinstance(data, dict)
        table_meta = cls.get_table_meta()
        filtered_fields = {
            f_name: f_val
            for f_name, f_val in data.items()
            if f_name in table_meta and f_val is not UNSET
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
        pk_set: set[FieldName] = set(cls.get_pk_names())
        table_meta = cls.get_table_meta()

        for field_name, field_meta in table_meta.items():
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
        table_meta = self.get_table_meta()
        data = {
            field_name: getattr(self, field_name, UNSET) for field_name in table_meta
        }  # get current field values, default to UNSET if missing
        # filter out UNSET fields
        filtered_data = self._filter_data(data)
        self.validate_data(filtered_data)
        return filtered_data

    def insert_to_db(
        self,
        cur: sqlite3.Cursor,
        simulate: bool = False,
        on_conflict: bool = False,
    ) -> None:
        if not simulate and not cur:
            raise ValueError(err_msg("'cur' is required"))

        pk_names = self.get_pk_names()
        data = self.validate_fields()
        self._validate_insert_data(data)
        cols = ",\n    ".join(data.keys())
        placeholders = ",\n    ".join(f":{col}" for col in data.keys())
        sql = dedent(f"""
        INSERT INTO {self.get_table_name()} (
            {cols}
        ) VALUES (
            {placeholders}
        );
        """)
        if on_conflict:
            pks = ", ".join(pk_names)
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
            raise ValueError(err_msg("'cur' is required"))

        pk_names = self.get_pk_names()
        data = self.validate_fields()
        update_cols = [k for k in data.keys() if k not in pk_names]
        if not update_cols:
            return False  # nothing to update
        set_clause = ",\n    ".join(f"{col} = :{col}" for col in update_cols)
        where_clause = " AND\n    ".join(f"{pk_col} = :{pk_col}" for pk_col in pk_names)
        sql = dedent(f"""
        UPDATE {self.get_table_name()}
        SET
            {set_clause}
        WHERE
            {where_clause};
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
        if not simulate and not cur:
            raise ValueError(err_msg("'cur' is required"))

        pk_names = self.get_pk_names()
        data = self.validate_fields()
        where_clause = " AND\n    ".join(f"{pk_col} = :{pk_col}" for pk_col in pk_names)
        params = {pk_col: data[pk_col] for pk_col in pk_names}
        sql = dedent(f"""
        SELECT 1 FROM {self.get_table_name()}
        WHERE
            {where_clause};
        """)
        if not simulate:
            cur.execute(sql, params)
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
