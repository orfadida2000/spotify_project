import types
from collections import Counter
from collections.abc import Sequence
from types import resolve_bases
from typing import Any, Protocol, TypeVar, runtime_checkable

BUILTINS = types.ModuleType("builtins")


T = TypeVar("T")


class MROError(TypeError):
    """Raised when C3 linearization cannot compute an MRO."""


class C3MergeError(TypeError):
    """Raised when C3 linearization cannot computed a merge sequence."""

    def __init__(self, msg: str, *, rem_seqs: list[list[T]]):
        rem_seqs_str = "\n".join(f"{seq!r}" for seq in rem_seqs)
        super().__init__(
            f"{msg}\nThe remaining sequences that could not be merged are:\n{rem_seqs_str}"
        )
        self.rem_seqs = rem_seqs


def c3_merge(seqs: Sequence[Sequence[T]]) -> list[T]:
    """
    Efficient C3 merge.

    seqs: a sequence of sequences (each non-empty or empty). The merge will
          consume them conceptually without mutating the inputs.

    Returns the merged linearization (without the implicit "new class" head).

    Raises MROError if no consistent C3 linearization exists.
    """
    # Materialize as lists for O(1) indexing and keep per-seq head indices.
    lists: list[list[T]] = []
    total_len: int = 0
    for seq in seqs:
        curr_lst = list(seq)
        if not curr_lst:
            continue
        curr_set = set(curr_lst)
        if len(curr_set) != len(curr_lst):
            raise TypeError("Input sequences to c3_merge must not contain duplicates")
        lists.append(curr_lst)
        total_len += len(curr_lst)
    num_nonempty_lists = len(lists)
    if num_nonempty_lists == 0:
        return []

    heads: list[int] = [0] * num_nonempty_lists  # current head index per list

    # Count how many tails currently contain each element.
    # Tail means all elements after the current head in that list.
    in_tails: Counter[T] = Counter()

    # Map element -> set of list indices where it is currently the head.
    head_to_lists: dict[T, set[int]] = {}

    for lst_idx, lst in enumerate(lists):
        curr_head_idx = heads[lst_idx]
        # Initialize tail counts
        in_tails.update(lst[curr_head_idx + 1 :])  # tail elements
        # Initialize head to lists mapping
        head_to_lists.setdefault(lst[curr_head_idx], set()).add(lst_idx)

    merged_lst: list[T] = []

    def advance_list(lst_idx: int) -> None:
        """Advance list lst_idx by one head position (removing its current head)."""
        lst = lists[lst_idx]
        old_head_idx = heads[lst_idx]
        old_head = lst[old_head_idx]

        # Remove lst_idx from the old head bucket.
        lst_idxs_bucket = head_to_lists.get(old_head, None)
        assert lst_idxs_bucket is not None, "Inconsistent head to lists state"
        lst_idxs_bucket.discard(lst_idx)
        # If no more lists have this as head, remove the bucket.
        if not lst_idxs_bucket:
            del head_to_lists[old_head]

        # Advance head index.
        new_head_idx = old_head_idx + 1
        heads[lst_idx] = new_head_idx
        if new_head_idx >= len(lst):
            return  # list exhausted

        # Update head to lists mapping with the new head.
        new_head = lst[new_head_idx]
        head_to_lists.setdefault(new_head, set()).add(lst_idx)

        # The new head was previously part of this list's tail; now it's head,
        # so remove one tail occurrence for it.
        assert in_tails.get(new_head, 0) > 0, "Inconsistent tail count state"
        in_tails[new_head] -= 1
        if in_tails[new_head] == 0:
            del in_tails[new_head]

    remaining = total_len

    while remaining > 0:
        # Pop until we find a non-stale, actually-eligible head element.
        picked: T | None = None
        for lst_idx, lst in enumerate(lists):
            curr_head_idx = heads[lst_idx]
            if curr_head_idx >= len(lst):
                continue  # list exhausted

            curr_head = lst[curr_head_idx]
            # Check if curr_head is eligible (not in any tail).
            if in_tails.get(curr_head, 0) == 0:
                picked = curr_head
                break

        if picked is None:
            # No eligible head exists: C3 conflict.
            # Provide a readable summary of remaining heads for debugging.
            rem_seqs = [
                lists[lst_idx]
                for lst_idx in range(num_nonempty_lists)
                if heads[lst_idx] < len(lists[lst_idx])
            ]
            raise C3MergeError(
                "Cannot merge sequences to compute C3 linearization", rem_seqs=rem_seqs
            )

        merged_lst.append(picked)

        # Advance *all* lists whose head is the picked element.
        assert picked in head_to_lists, "Inconsistent head to lists state"
        idxs = list(head_to_lists[picked])  # copy because each advance_list mutates the set value
        for lst_idx in idxs:
            # Before advancing, remove tail membership contributed by the old head's removal:
            # When we remove old head from a list, the element immediately after it (new head)
            # gets removed from that list's tail. Elements after the new head remain in the tail,
            # so only the new head needs decrement (handled in advance_list).
            advance_list(lst_idx)
            remaining -= 1

        # After advancing lists, new heads might have become eligible due to tail-count changes.
        # We already enqueue new heads when their tail count hits zero in advance_list().
        # But we also need to enqueue any *existing* head elements whose in_tails became zero
        # due to decrements. That happens only for new_head in advance_list, so covered.

    return merged_lst


@runtime_checkable
class SupportsMROEntries(Protocol):
    def __mro_entries__(self, bases: tuple[object]) -> tuple[Any, ...]: ...


def compute_mro(
    *, cls: type | None, bases: Sequence[type | SupportsMROEntries] | None
) -> tuple[type, ...]:
    """
    Compute the MRO order of a class.

    If `cls` is given, compute the MRO of that class (uses its __bases__ attribute), should be equivalent to `cls.__mro__`.
    If `bases` is given, compute the MRO of a hypothetical class with those bases,
    should be equivalent to the MRO of a hypothetical class without the new class itself (the first element).

    Args:
      cls (type | None): if given, the new class itself (to be prepended to the MRO tail)
      bases (Sequence[type | SupportsMROEntries] | None): direct base classes of the new class (in declaration order)

    Returns:
        tuple[type, ...]: the computed MRO order

    Raises:
        TypeError: if the arguments are of invalid types (see Notes).
        TypeError: if an appropriate metaclass cannot be determined from the bases (relevant only if `bases` is given).
        MROError: if the C3 linearization algorithm cannot compute a valid MRO order.

    Notes:
        - Exactly one of `cls` or `bases` must be given (the other must be None).
        - If `bases` is given, it must be a sequence where each element is either a class object (instance of `type`)
          or implements the `__mro_entries__` protocol (see PEP 560) if it's not an instance of `type`.
        - If `bases` is given, any non-class elements implementing `__mro_entries__` will be replaced by the result of calling
          their `__mro_entries__` method with the full `bases` tuple as argument or will be discarded if the result is an empty tuple.
          If a non-class element's `does not implement `__mro_entries__`, or if its `__mro_entries__` method doesn't return a tuple of classes, a TypeError is raised.
        - The MRO is computed using the C3 linearization algorithm.
    """
    if cls is not None:
        if not isinstance(cls, type):
            raise TypeError(
                f"cls argument must be None or a class (an instance of type), got {type(cls).__name__}"
            )
        if bases is not None:
            raise TypeError(
                f"when cls argument is given, bases argument must be None, got {type(bases).__name__}"
            )
        # when cls is given, the bases argument is ignored and taken from the class itself (cls.__bases__)
        bases = cls.__bases__
    else:
        if not isinstance(bases, Sequence):
            raise TypeError(
                f"bases argument must be None or a sequence, got {type(bases).__name__}"
            )
        if cls is not None:
            raise TypeError(
                f"when bases argument is given, cls argument must be None, got {type(cls).__name__}"
            )
        # when cls is None, we assume at least object as base if bases is empty
        # we assume that the mro order that will be computed isn't for the class object itself
        bases = tuple(bases) or (object,)
        bases = resolve_bases(bases)
        # validate that all after resolution, all bases are indeed classes
        for b in bases:
            if not isinstance(b, type):
                raise TypeError(
                    f"The post resolution bases must be a sequence of classes (instances of type), got {type(b).__name__} in bases"
                )

        mcls_cands = tuple({type(b) for b in bases})
        mcls = None
        for cand in mcls_cands:
            if all(issubclass(cand, other) for other in mcls_cands):
                mcls = cand
                break
        if mcls is None:
            raise TypeError("Cannot determine an appropriate metaclass based on the bases argument")

    seqs: list[Sequence[type]] = [b.__mro__ for b in bases]
    seqs.append(bases)
    mro_tail = c3_merge(seqs)

    if cls is not None:
        mro_order = [cls] + mro_tail
    else:
        mro_order = mro_tail
    return tuple(mro_order)


def get_slot_map(cls: type, recursive: bool = False, strict: bool = False) -> dict[str, type]:
    """
    Return a dict mapping of attribute names whose values are CPython slot
    member descriptors (i.e., created by `__slots__`) into the class they
    were defined in (i.e., the class where the `__slots__` entry was declared).

    Args:
        cls (type): the class to inspect
        recursive (bool, optional): if True, inspect all classes in `cls.__mro__`.
                                    if False, inspect only `cls.__dict__` (first class in the MRO). Defaults to False.
        strict (bool, optional): if True, raise ValueError if a slot name is defined in multiple classes in the MRO.
                                 if False, map to the first class in the MRO where it is defined (most-derived first). Defaults to False.

    Returns:
        dict[str, type]: mapping of slot member names to the class they were defined in.

    Raises:
        ValueError: if `strict=True` and a slot name is defined in multiple classes in the MRO.
        RuntimeError: if `types.MemberDescriptorType` is not available in `types`.
        TypeError: if `cls` is not an instance of `type`, or if `strict` is not a bool, or if `recursive` is not a bool.

    Notes:
        - CPython-specific: `__slots__` entries are exposed as instances of
          `types.MemberDescriptorType` in `cls.__dict__`(other implementations may differ).
        - If `MemberDescriptorType` is not available in `types`, this function will raise a RuntimeError.
        - This function inspects only `cls.__dict__` (not inherited slots) unless `recursive=True`,
          in which case it inspects all classes in `cls.__mro__`.
        - If a slot name is defined in multiple classes in the MRO, it would map to the first class
          in the MRO where it is defined (unless `strict=True`, see below), in accordance with Python's attribute lookup order (most-derived first).
          (Python technically allows duplicate slot names in multiple base classes, but it's discouraged — might cause unexpected behavior, and a check against it may be added in future versions).
        - If `strict=True`, and a slot name is defined in multiple classes in the MRO, a ValueError is raised.

    """
    if not isinstance(cls, type):
        raise TypeError(
            f"cls argument must be a class (an instance of type), got {type(cls).__name__}"
        )
    if not isinstance(recursive, bool):
        raise TypeError(f"recursive argument must be a bool, got {type(recursive).__name__}")
    if not isinstance(strict, bool):
        raise TypeError(f"strict argument must be a bool, got {type(strict).__name__}")
    if not hasattr(types, "MemberDescriptorType"):
        raise RuntimeError(
            "types.MemberDescriptorType is not available in this Python implementation"
        )

    slot_members: dict[str, type] = {}
    classes_to_inspect = cls.__mro__ if recursive else (cls,)
    for base_cls in classes_to_inspect:
        for name, value in base_cls.__dict__.items():
            if isinstance(value, types.MemberDescriptorType):
                if name in slot_members:
                    if strict:
                        raise ValueError(
                            f"Slot name {name!r} defined in multiple classes in the MRO (first seen in {slot_members[name].__name__} and later in {base_cls.__name__})"
                        )
                    # else: non-strict mode, keep the first occurrence (most-derived class)
                    continue
                else:
                    slot_members[name] = base_cls
    return slot_members


def class_instances_have_dict(cls: type) -> bool:
    """
    Return True iff instances of `cls` have a `__dict__` attribute.

    CPython details:
        - `cls.__dictoffset__ == 0`  => no instance dict
        - `cls.__dictoffset__ > 0`   => dict stored at a fixed offset
        - `cls.__dictoffset__ == -1` => managed dict (CPython 3.12+)

    Args:
        cls (type): the class to inspect

    Returns:
        bool: True iff instances of `cls` have a `__dict__` attribute.

    Raises:
        TypeError: if `cls` is not an instance of `type`.
    """
    if not isinstance(cls, type):
        raise TypeError("cls argument must be a class (an instance of type)")
    return cls.__dictoffset__ != 0


def class_instances_support_weakref(cls: type) -> bool:
    """
    Return True iff instances of `cls` are weak-referenceable.

    CPython details:
        - `cls.__weakrefoffset__ == 0` => not weakref-able
        - `cls.__weakrefoffset__ > 0`  => classic weakref list at a fixed offset
        - `cls.__weakrefoffset__ < 0`  => managed weakref (CPython 3.12+)

    Args:
        cls (type): the class to inspect

    Returns:
        bool: True iff instances of `cls` are weak-referenceable.

    Raises:
        TypeError: if `cls` is not an instance of `type`.
    """
    if not isinstance(cls, type):
        raise TypeError("cls argument must be a class (an instance of type)")
    return cls.__weakrefoffset__ != 0
