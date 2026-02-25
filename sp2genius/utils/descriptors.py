from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")
InstanceT = TypeVar("InstanceT")


@dataclass(frozen=True, slots=True)
class WriteOnceSlot(Generic[T]):
    """
    Wrap a CPython slot descriptor (member_descriptor) and allow setting only once.
    """

    _orig_slot_desc: Any
    allow_delete: bool = field(default=False, kw_only=True)
    allow_reassign_after_delete: bool = field(default=False, kw_only=True)
    _deleted_before: bool = field(default=False, init=False)

    # populated via __set_name__
    _name: str | None = field(default=None, init=False)

    # Introspection metadata (not required for semantics, but helpful), also populated via __set_name__
    __objclass__: type | None = field(default=None, init=False)

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "__objclass__", owner)
        object.__setattr__(self, "_name", name)

    def __get__(self, instance: Any, owner: type | None = None) -> T:
        if instance is None:
            return self  # type: ignore[return-value]
        return self._orig_slot_desc.__get__(instance, owner)

    def __set__(self, instance: Any, value: T) -> None:
        # Disallow reassignment if currently set.
        try:
            self._orig_slot_desc.__get__(instance, type(instance))
        except AttributeError:
            # Not set yet; allow setting only if not deleted before (or if re-assign after delete is allowed).
            if self._deleted_before and not self.allow_reassign_after_delete:
                name = self._name or "<slot>"
                raise AttributeError(
                    f"'{name}' was already deleted, re-assignment is disallowed; "
                ) from None
            self._orig_slot_desc.__set__(instance, value)
            return

        name = self._name or "<slot>"
        raise AttributeError(f"'{name}' is write-once and is already set")

    def __delete__(self, instance: Any) -> None:
        if not self.allow_delete:
            name = self._name or "<slot>"
            raise AttributeError(f"'{name}' cannot be deleted")

        self._orig_slot_desc.__delete__(instance)
        object.__setattr__(self, "_deleted_before", True)


def write_once_slots(
    *,
    allow_delete: bool = False,
    allow_reassign_after_delete: bool = False,
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    """
    Class decorator: wraps each local slot descriptor with WriteOnceSlot.

    - Wraps all slot names found in the class's *own* __slots__.
    - Skips '__dict__' and '__weakref__'.
    - If __slots__ is missing or empty in the class namespace, returns class unchanged.
    """

    def deco(cls: type[InstanceT]) -> type[InstanceT]:
        if not isinstance(cls, type):
            raise TypeError("@write_once_slots can only be applied to classes")
        if not isinstance(allow_delete, bool):
            return cls
        if not isinstance(allow_reassign_after_delete, bool):
            return cls

        # Only act on slots defined *locally* in this class body.
        raw_slots = cls.__dict__.get("__slots__", None)
        if raw_slots is None:
            return cls

        # Normalize __slots__ as an iterable of names.
        if isinstance(raw_slots, str):
            slot_names = (raw_slots,)
        else:
            try:
                slot_names = tuple(raw_slots)
            except TypeError:
                # Non-iterable / weird __slots__ -> treat as "no slots"
                return cls

        # Empty iterator / empty tuple / etc.
        if not slot_names:
            return cls

        for name in slot_names:
            # Skip special slots.
            if not isinstance(name, str):
                continue
            if name in ("__dict__", "__weakref__"):
                continue

            # Must exist in cls.__dict__ if it's a local slot; otherwise skip.
            curr_slot_desc = cls.__dict__.get(name, None)
            if curr_slot_desc is None:
                continue

            wrapper = WriteOnceSlot(
                curr_slot_desc,
                allow_delete=allow_delete,
                allow_reassign_after_delete=allow_reassign_after_delete,
            )

            # Install wrapper (normal attribute assignment on the class).
            setattr(cls, name, wrapper)

            # Emulate class-creation binding hook.
            # Also populates __objclass__ and _name metadata on the wrapper descriptor.
            wrapper.__set_name__(cls, name)

        return cls

    return deco
