from collections.abc import Mapping, Sequence
from typing import Any


class SpecFilterError(ValueError):
    """Base class for all errors raised by filter_by_spec()."""

    def __init__(self, message: str, *, path: str | None = None):
        if path:
            message = f"{message} (at path={path})"
        super().__init__(message)
        self.path = path


class InvalidSpecError(SpecFilterError):
    """Raised when the SPEC itself is invalid or malformed."""

    pass


class SpecDataMismatchError(SpecFilterError):
    """Raised when data structure does not match the spec structure."""

    pass


class SpecTypeError(SpecFilterError):
    """Raised when a leaf value does not satisfy the type spec."""

    pass


def _filter(node: Any, node_spec: Any, path: str = "<root>") -> Any:
    if isinstance(node_spec, tuple):  # for leaf specs allowing multiple types
        if not node_spec:
            raise InvalidSpecError(
                "Tuple spec must not be empty",
                path=path,
            )
        if not all(isinstance(t, type) for t in node_spec):
            raise InvalidSpecError(
                "Tuple spec must contain only types",
                path=path,
            )

        if isinstance(node, node_spec):
            return node
        else:
            raise SpecTypeError(
                f"Expected one of types: {tuple(t.__name__ for t in node_spec)}, "
                f"got {type(node).__name__}",
                path=path,
            )

    if isinstance(node_spec, type):  # for leaf specs allowing a single type
        if isinstance(node, node_spec):
            return node
        else:
            raise SpecTypeError(
                f"Expected type: {node_spec.__name__}, got {type(node).__name__}",
                path=path,
            )

    # Dict node with dict spec (no __sequence__ → plain nested dict)
    if isinstance(node_spec, dict) and isinstance(node, Mapping):
        result: dict[str, Any] = {}
        for key, sub_spec in node_spec.items():
            if key not in node:
                continue
            sub_path = f"{path}.{key}" if path else key
            filtered_value = _filter(node[key], sub_spec, sub_path)
            result[key] = filtered_value
        return result

    # List node with list-element spec: {"__list__": { ... }}
    if (
        isinstance(node_spec, list)
        and isinstance(node, Sequence)
        and not isinstance(node, (str, bytes, bytearray))  # exclude string-like sequences
    ):
        spec_len = len(node_spec)
        if spec_len > 1:
            raise InvalidSpecError(
                "List spec must have at most one element (the element spec)",
                path=path,
            )

        if spec_len == 0:
            # Empty sequence spec: always return empty list regardless of node contents
            return []

        elem_spec = node_spec[0]
        result_list: list[Any] = []
        for idx, elem in enumerate(node):
            elem_path = f"{path}[{idx}]"
            filtered_elem = _filter(elem, elem_spec, elem_path)
            result_list.append(filtered_elem)
        return result_list

    # Shape mismatch or unsupported combination
    raise SpecDataMismatchError(
        "Shape mismatch between data and spec or unsupported combination "
        f"(data type: {type(node).__name__}, spec type: {type(node_spec).__name__})",
        path=path,
    )


def filter_by_spec(data: Any, spec: Any) -> Any:
    filtered = _filter(data, spec, "<root>")
    return filtered


__all__ = [
    "filter_by_spec",
    "SpecFilterError",
    "InvalidSpecError",
    "SpecDataMismatchError",
    "SpecTypeError",
]
