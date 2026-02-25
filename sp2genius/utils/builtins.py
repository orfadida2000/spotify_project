import builtins
import textwrap
from collections.abc import Mapping, Sequence, Set
from types import MappingProxyType
from typing import Final

from .class_introspection import (
    class_instances_have_dict,
    class_instances_support_weakref,
    get_slot_map,
)
from .console import (
    TermForegroundColor,
    TermTextAttribute,
    colorize_text,
    init_console,
)
from .descriptors import write_once_slots


@write_once_slots(allow_delete=False)
class BuiltinAnalysis:
    """
    Analyzes Python built-in classes for subclassability and __slots__ permissions.

    This class uses __slots__ to optimize memory usage and prevent dynamic attribute creation.
    It also wrap those the slot members data descriptors with a custom write-once descriptor to
    prevent modification after initialization. It does it by decorating the class definition with
    @write_once_slots(allow_delete=False) (return a callable that act as a class decorator).
    In addition, after it finishes the analysis during __init__, it makes sure that each attribute is immutable or
    effectively immutable by using immutable types (e.g. tuples, frozensets) or in the case of mappings,
    it creates a shallow copy dictionary of it and expose the attribute as a read-only type (i.e. MappingProxyType) of this dictionary.
    Since it doesn't leave any pointers to this dictionary, the attribute is effectively immutable.
    If transform mutable object into their immutable counterparts not only for the top-level attribute but also for nested mutable objects inside them.

    Attributes:
        Class Attributes:
            __slots__ (tuple[str, ...]): defines the allowed attribute names for instances of this class.
            _BUILTIN_TYPES (frozenset[type]): a frozenset containing all built-in types in Python (computed using the builtins module).

        Instance Attributes:
            builtin_types (tuple[type, ...]): a tuple of built-in types to analyze, if not provided during initialization defaults to all built-in types.
            builtins_analysis (MappingProxyType[type, MappingProxyType[str, bool]]): a read-only mapping containing analysis results for each built-in type.
                For each built-in type, it maps the it to the results of its analysis (i.e. subclassability and __slots__ permissions) as a nested read-only mapping.
            subclassability_analysis (MappingProxyType[str, frozenset[type]]): a read-only mapping that categorizes built-in types into 2 categories: subclassable and non-subclassable.
            slot_permissions_analysis (MappingProxyType[str, frozenset[type]]): a read-only mapping that categorizes built-in types based on their __slots__ permissions into 8 categories:
                allowing/disallowing empty __slots__, basic string in __slots__, `__dict__` in __slots__, and `__weakref__` in __slots__.
    """

    __slots__ = (
        "builtin_types",
        "builtins_analysis",
        "subclassability_analysis",
        "slot_permissions_analysis",
    )
    _BUILTIN_TYPES = frozenset(obj for name, obj in vars(builtins).items() if isinstance(obj, type))

    def __init__(self, builtin_types: Sequence[type] | None = None) -> None:
        """
        Initializes the BuiltinAnalysis instance.

        Given a sequence of built-in types, performs analysis on their subclassability
        and __slots__ permissions (see notes). If no sequence is provided, analyzes all built-in types.

        Args:
            builtin_types (Sequence[type] | None, optional): A sequence of built-in types to analyze.
                If None, all built-in types are analyzed. Defaults to None.

        Raises:
            TypeError: if builtin_types is not a sequence of types.
            ValueError: if any type in builtin_types is not a built-in type.

        Notes:
            - Subclassability: Determines if a built-in type can be subclassed.
            - __slots__ Permissions: For subclassable built-in types, checks the following:
                - Allows empty __slots__
                - Allows basic string (e.g., 'foo') in __slots__
                - Allows `__dict__` in __slots__
                - Allows `__weakref__` in __slots__
            - The analysis results are stored in read-only mappings which cannot be modified after initialization.
            - The analysis results in the following attributes:
                - builtins_analysis: Mapping[type, Mapping[str, bool]] - per built-in class analysis
                - subclassability_analysis: Mapping[str, Set[type]] - subclassability categories
                - slot_permissions_analysis: Mapping[str, Set[type]] - __slots__ permissions categories
        """
        if builtin_types is None:
            builtin_types_tuple = tuple(BuiltinAnalysis._BUILTIN_TYPES)
        else:
            if not isinstance(builtin_types, Sequence):
                raise TypeError(
                    f"builtin_types must be a sequence of elements, got {type(builtin_types).__name__}"
                )
            seen_types = set()
            for t in builtin_types:
                if not isinstance(t, type):
                    raise TypeError(
                        f"All elements of builtin_types must be types, got {type(t).__name__}"
                    )
                if t not in BuiltinAnalysis._BUILTIN_TYPES:
                    raise ValueError(f"The type {t.__name__} is not a built-in type.")
                # duplicate built-in type is allowed but ignored
                if t in seen_types:
                    continue
                seen_types.add(t)
            builtin_types_tuple = tuple(seen_types)

        self.builtin_types: tuple[type, ...] = builtin_types_tuple
        self.analyze_builtin_types()

    @staticmethod
    def is_subclassable_type(type_obj: type) -> bool:
        try:
            dummy_cls = type(f"_Test_{type_obj.__name__}", (type_obj,), {})
            assert dummy_cls is not None and issubclass(dummy_cls, type_obj)
            return True
        except TypeError:
            return False

    @staticmethod
    def inspect_slots_permission(base: type, slot: str | None) -> bool:
        if not BuiltinAnalysis.is_subclassable_type(base):
            raise TypeError(
                f"The argument {base.__name__} is not subclassable, cannot inspect __slots__ permission."
            )
        try:
            ns = {}
            if isinstance(slot, str):
                slots_val: tuple[str, ...] = (slot,) if slot else ()
                ns["__slots__"] = slots_val
            type(f"_SlotsTest_{base.__name__}", (base,), ns)
            return True
        except TypeError:
            return False

    @staticmethod
    def allows_no_slots(type_obj: type) -> bool:
        return BuiltinAnalysis.inspect_slots_permission(type_obj, None)

    @staticmethod
    def allows_empty_slots(type_obj: type) -> bool:
        return BuiltinAnalysis.inspect_slots_permission(type_obj, "")

    @staticmethod
    def allows_basic_slots(type_obj: type) -> bool:
        return BuiltinAnalysis.inspect_slots_permission(type_obj, "foo")

    @staticmethod
    def allows_dict_slots(type_obj: type) -> bool:
        return BuiltinAnalysis.inspect_slots_permission(type_obj, "__dict__")

    @staticmethod
    def allows_weakref_slots(type_obj: type) -> bool:
        return BuiltinAnalysis.inspect_slots_permission(type_obj, "__weakref__")

    @staticmethod
    def get_all_builtin_types() -> tuple[type, ...]:
        return tuple(BuiltinAnalysis._BUILTIN_TYPES)

    @classmethod
    def is_builtin_type(cls, type_obj: type) -> bool:
        if not isinstance(type_obj, type):
            return False
        return type_obj in cls._BUILTIN_TYPES

    def analyze_builtin_types(self) -> None:
        cls = type(self)

        # Prepare subclassability analysis data structures
        subclassability_analysis_key_order: tuple[str, ...] = (
            "subclassable_builtins",
            "non_subclassable_builtins",
        )
        subclassability_analysis: dict[str, set[type]] = {
            key: set() for key in subclassability_analysis_key_order
        }

        # Prepare slot permissions analysis data structures
        slot_permissions_analysis_key_order: tuple[str, ...] = (
            "allowing_no_slots",
            "disallowing_no_slots",
            "allowing_empty_slots",
            "disallowing_empty_slots",
            "allowing_basic_slots",
            "disallowing_basic_slots",
            "allowing_dict_slots",
            "disallowing_dict_slots",
            "allowing_weakref_slots",
            "disallowing_weakref_slots",
        )
        slot_permissions_analysis: dict[str, set[type]] = {
            key: set() for key in slot_permissions_analysis_key_order
        }

        # Prepare per built-in class analysis data structure
        builtins_analysis: dict[type, dict[str, bool | tuple[str, ...]]] = {}

        for builtin_cls in self.builtin_types:
            builtins_analysis[builtin_cls] = {}

            slots = sorted(get_slot_map(cls=builtin_cls, recursive=False).keys())
            builtins_analysis[builtin_cls]["slots"] = tuple(slots)

            if class_instances_have_dict(builtin_cls):
                builtins_analysis[builtin_cls]["instances_support_dict"] = True
            else:
                builtins_analysis[builtin_cls]["instances_support_dict"] = False

            if class_instances_support_weakref(builtin_cls):
                builtins_analysis[builtin_cls]["instances_support_weakref"] = True
            else:
                builtins_analysis[builtin_cls]["instances_support_weakref"] = False

            if cls.is_subclassable_type(builtin_cls):
                subclassability_analysis["subclassable_builtins"].add(builtin_cls)
                builtins_analysis[builtin_cls]["subclassable"] = True
            else:
                subclassability_analysis["non_subclassable_builtins"].add(builtin_cls)
                builtins_analysis[builtin_cls]["subclassable"] = False

        for builtin_cls in subclassability_analysis["subclassable_builtins"]:
            if cls.allows_no_slots(builtin_cls):
                slot_permissions_analysis["allowing_no_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_no_slots"] = True
            else:
                slot_permissions_analysis["disallowing_no_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_no_slots"] = False

            if cls.allows_empty_slots(builtin_cls):
                slot_permissions_analysis["allowing_empty_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_empty_slots"] = True
            else:
                slot_permissions_analysis["disallowing_empty_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_empty_slots"] = False

            if cls.allows_basic_slots(builtin_cls):
                slot_permissions_analysis["allowing_basic_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_basic_slots"] = True
            else:
                slot_permissions_analysis["disallowing_basic_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_basic_slots"] = False

            if cls.allows_dict_slots(builtin_cls):
                slot_permissions_analysis["allowing_dict_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_dict_slots"] = True
            else:
                slot_permissions_analysis["disallowing_dict_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_dict_slots"] = False

            if cls.allows_weakref_slots(builtin_cls):
                slot_permissions_analysis["allowing_weakref_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_weakref_slots"] = True
            else:
                slot_permissions_analysis["disallowing_weakref_slots"].add(builtin_cls)
                builtins_analysis[builtin_cls]["allowing_weakref_slots"] = False

        self.builtins_analysis: MappingProxyType[
            type, MappingProxyType[str, bool | tuple[str, ...]]
        ] = MappingProxyType(
            {
                builtin_cls: MappingProxyType(analysis)
                for builtin_cls, analysis in builtins_analysis.items()
            }
        )
        self.subclassability_analysis: MappingProxyType[str, frozenset[type]] = MappingProxyType(
            {key: frozenset(classes) for key, classes in subclassability_analysis.items()}
        )
        self.slot_permissions_analysis: MappingProxyType[str, frozenset[type]] = MappingProxyType(
            {key: frozenset(classes) for key, classes in slot_permissions_analysis.items()}
        )

    @staticmethod
    def _report_aggregated_results(analysis: Mapping[str, Set[type]]) -> None:
        for category, classes in sorted(analysis.items(), key=lambda item: item[0]):
            if not classes:
                category_header_str = f"{category}: <empty>"
            else:
                category_header_str = (
                    f"{category}: {len(classes)} {'item' if len(classes) == 1 else 'items'}"
                )

            print(category_header_str)
            for cls in sorted(classes, key=lambda c: c.__name__):
                print(f"  - {cls.__name__}")
            print()

    def get_subclassable_builtins(self) -> frozenset[type]:
        return self.subclassability_analysis["subclassable_builtins"]

    def get_non_subclassable_builtins(self) -> frozenset[type]:
        return self.subclassability_analysis["non_subclassable_builtins"]

    def get_builtins_allowing_no_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["allowing_no_slots"]

    def get_builtins_disallowing_no_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["disallowing_no_slots"]

    def get_builtins_allowing_empty_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["allowing_empty_slots"]

    def get_builtins_disallowing_empty_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["disallowing_empty_slots"]

    def get_builtins_allowing_basic_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["allowing_basic_slots"]

    def get_builtins_disallowing_basic_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["disallowing_basic_slots"]

    def get_builtins_allowing_dict_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["allowing_dict_slots"]

    def get_builtins_disallowing_dict_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["disallowing_dict_slots"]

    def get_builtins_allowing_weakref_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["allowing_weakref_slots"]

    def get_builtins_disallowing_weakref_slots(self) -> frozenset[type]:
        return self.slot_permissions_analysis["disallowing_weakref_slots"]

    @staticmethod
    def clean_multiline_string(s: str, *, indent_reps: int, indent_str: str = "  ") -> str:
        dedented_s = textwrap.dedent(s)
        dedented_strip_newlines_s = dedented_s.strip("\n")
        dedented_strip_newlines_indented_s = textwrap.indent(
            dedented_strip_newlines_s, indent_str * indent_reps
        )

        cleaned_s = dedented_strip_newlines_indented_s
        return cleaned_s

    def report_subclassability_results(self) -> None:
        print("Built-in types subclassability analysis results:")

        subclassable_builtins = self.get_subclassable_builtins()
        non_subclassable_builtins = self.get_non_subclassable_builtins()
        if not non_subclassable_builtins:
            print(f"  All {len(subclassable_builtins)} built-in types are subclassable.\n")
        elif not subclassable_builtins:
            print(f"  All {len(non_subclassable_builtins)} built-in types are non-subclassable.\n")
        else:
            print("  The following built-in types are subclassable:")
            for builtin_cls in sorted(subclassable_builtins, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(subclassable_builtins)}\n")

            print("  The following built-in types are non-subclassable:")
            for builtin_cls in sorted(non_subclassable_builtins, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(non_subclassable_builtins)}\n")

    def report_slot_permissions_results(self) -> None:
        print("Built-in types __slots__ permissions analysis results:")

        allowing_no_slots = self.get_builtins_allowing_no_slots()
        disallowing_no_slots = self.get_builtins_disallowing_no_slots()
        if not disallowing_no_slots:
            print(
                f"  All {len(allowing_no_slots)} subclassable built-in types allow no __slots__ attribute.\n"
            )
        elif not allowing_no_slots:
            print(
                f"  All {len(disallowing_no_slots)} subclassable built-in types disallow no __slots__ attribute.\n"
            )
        else:
            print("  The following subclassable built-in types allow no __slots__ attribute:")
            for builtin_cls in sorted(allowing_no_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(allowing_no_slots)}\n")

            print("  The following subclassable built-in types disallow no __slots__ attribute:")
            for builtin_cls in sorted(disallowing_no_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(disallowing_no_slots)}\n")

        allowing_empty_slots = self.get_builtins_allowing_empty_slots()
        disallowing_empty_slots = self.get_builtins_disallowing_empty_slots()
        if not disallowing_empty_slots:
            print(
                f"  All {len(allowing_empty_slots)} subclassable built-in types allow empty __slots__.\n"
            )
        elif not allowing_empty_slots:
            print(
                f"  All {len(disallowing_empty_slots)} subclassable built-in types disallow empty __slots__.\n"
            )
        else:
            print("  The following subclassable built-in types allow empty __slots__:")
            for builtin_cls in sorted(allowing_empty_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(allowing_empty_slots)}\n")

            print("  The following subclassable built-in types disallow empty __slots__:")
            for builtin_cls in sorted(disallowing_empty_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(disallowing_empty_slots)}\n")

        allowing_basic_slots = self.get_builtins_allowing_basic_slots()
        disallowing_basic_slots = self.get_builtins_disallowing_basic_slots()
        if not disallowing_basic_slots:
            print(
                f"  All {len(allowing_basic_slots)} subclassable built-in types allow basic string in __slots__.\n"
            )
        elif not allowing_basic_slots:
            print(
                f"  All {len(disallowing_basic_slots)} subclassable built-in types disallow basic string in __slots__.\n"
            )
        else:
            print("  The following subclassable built-in types allow basic string in __slots__:")
            for builtin_cls in sorted(allowing_basic_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(allowing_basic_slots)}\n")

            print("  The following subclassable built-in types disallow basic string in __slots__:")
            for builtin_cls in sorted(disallowing_basic_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(disallowing_basic_slots)}\n")

        allowing_dict_slots = self.get_builtins_allowing_dict_slots()
        disallowing_dict_slots = self.get_builtins_disallowing_dict_slots()
        if not disallowing_dict_slots:
            print(
                f"  All {len(allowing_dict_slots)} subclassable built-in types allow `__dict__` in __slots__.\n"
            )
        elif not allowing_dict_slots:
            print(
                f"  All {len(disallowing_dict_slots)} subclassable built-in types disallow `__dict__` in __slots__.\n"
            )
        else:
            print("  The following subclassable built-in types allow `__dict__` in __slots__:")
            for builtin_cls in sorted(allowing_dict_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(allowing_dict_slots)}\n")

            print("  The following subclassable built-in types disallow `__dict__` in __slots__:")
            for builtin_cls in sorted(disallowing_dict_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(disallowing_dict_slots)}\n")

        allowing_weakref_slots = self.get_builtins_allowing_weakref_slots()
        disallowing_weakref_slots = self.get_builtins_disallowing_weakref_slots()
        if not disallowing_weakref_slots:
            print(
                f"  All {len(allowing_weakref_slots)} subclassable built-in types allow `__weakref__` in __slots__.\n"
            )
        elif not allowing_weakref_slots:
            print(
                f"  All {len(disallowing_weakref_slots)} subclassable built-in types disallow `__weakref__` in __slots__.\n"
            )
        else:
            print("  The following subclassable built-in types allow `__weakref__` in __slots__:")
            for builtin_cls in sorted(allowing_weakref_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(allowing_weakref_slots)}\n")

            print(
                "  The following subclassable built-in types disallow `__weakref__` in __slots__:"
            )
            for builtin_cls in sorted(disallowing_weakref_slots, key=lambda c: c.__name__):
                print(f"    - {builtin_cls.__name__}")
            print(f"      Total: {len(disallowing_weakref_slots)}\n")

    @classmethod
    def report_single_builtin_result(
        cls, builtin_cls: type, analysis: MappingProxyType[str, bool]
    ) -> None:
        yes_str = colorize_text("Yes", fg_color=TermForegroundColor.LIGHT_GREEN)
        no_str = colorize_text("No", fg_color=TermForegroundColor.LIGHT_RED)

        results_header = f"Results for built-in type: {colorize_text(builtin_cls.__name__, fg_color=TermForegroundColor.LIGHT_BLUE, text_attrs=[TermTextAttribute.BOLD])}"
        results_header = cls.clean_multiline_string(results_header, indent_reps=1)

        slots = analysis["slots"]
        instance_supports_dict = analysis["instances_support_dict"]
        instance_supports_weakref = analysis["instances_support_weakref"]
        is_subclassable = analysis["subclassable"]
        results = f"""
        - Instance analysis:
            · Slot members: {slots!r}
            · Supports __dict__: {yes_str if instance_supports_dict else no_str}
            · Supports __weakref__: {yes_str if instance_supports_weakref else no_str}
        - Subclassability analysis:
            · Is subclassable: {yes_str if is_subclassable else no_str}
        """
        results = cls.clean_multiline_string(results, indent_reps=2)

        if is_subclassable:
            slots_permissions_results = f"""
            - __slots__ permissions analysis:
                · Allows no __slots__ attribute: {yes_str if analysis["allowing_no_slots"] else no_str}
                · Allows empty __slots__: {yes_str if analysis["allowing_empty_slots"] else no_str}
                · Allows basic string (e.g. 'foo') in __slots__: {yes_str if analysis["allowing_basic_slots"] else no_str}
                · Allows `__dict__` in __slots__: {yes_str if analysis["allowing_dict_slots"] else no_str}
                · Allows `__weakref__` in __slots__: {yes_str if analysis["allowing_weakref_slots"] else no_str}
            """
            slots_permissions_results = cls.clean_multiline_string(
                slots_permissions_results, indent_reps=2
            )
            results = results + "\n" + slots_permissions_results

        final_report = results_header + "\n" + results
        print(final_report)
        print()

    def report_individual_results(self) -> None:
        cls = type(self)
        print("Per built-in type analysis results:")
        for builtin_cls, analysis in sorted(
            self.builtins_analysis.items(), key=lambda item: item[0].__name__
        ):
            cls.report_single_builtin_result(builtin_cls, analysis)

    def report_full_results(self) -> None:
        self.report_subclassability_results()
        self.report_slot_permissions_results()
        self.report_individual_results()


def main() -> None:
    all_builtins_analysis: Final[BuiltinAnalysis] = BuiltinAnalysis()
    all_builtins_analysis.report_subclassability_results()
    all_builtins_analysis.report_slot_permissions_results()

    # all_builtins_analysis.report_individual_results()


if __name__ == "__main__":
    init_console()
    main()
