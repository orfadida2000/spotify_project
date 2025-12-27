from collections.abc import Mapping, Sequence, Sized
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

    # Dict node with dict spec (plain nested dict)
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


def validate_normalize_fields(
    filtered_data: dict[str, Any],
    field_requirements: dict[str, bool],
    entity_name: str = "data",
) -> dict[str, Any]:
    """
    Validate and normalize fields in the given data dictionary based on the provided field requirements.

    Args:
        filtered_data (dict[str, Any]): The data dictionary to validate and normalize (assumed to be after filtering).
        field_requirements (dict[str, bool]): A dictionary specifying which fields are required (True)
            and which are optional (False).
        entity_name (str): The name of the entity being validated (for error messages), default is "data".

    Returns:
        dict[str, Any]: The normalized data dictionary with only the valid fields.

    Raises:
        TypeError: If the input filtered_data is not a dictionary.
        ValueError: If there are unexpected fields in the filtered_data (violates post-filtering assumptions), or if required fields are missing or empty.

    Note:
        - Optional fields that have empty values are filtered out from the returned dictionary.
        - All string fields are stripped of leading and trailing whitespace.
        - Empty values are defined as empty strings (post-stripping), empty containers (e.g., lists, dicts), or None.
    """

    def is_empty(value: Any) -> bool:
        value = value.strip() if isinstance(value, str) else value
        if value is None:
            return True
        if isinstance(value, (bool, int, float)):
            return False
        if isinstance(value, Sized):
            try:
                return len(value) == 0
            except Exception:
                return False
        return False

    if not isinstance(filtered_data, dict):
        raise TypeError(f"{entity_name} data must be a dictionary.")
    data_key_set = set(filtered_data.keys())
    fields_set = set(field_requirements.keys())
    extra_fields = data_key_set - fields_set
    if extra_fields:
        raise ValueError(f"{entity_name} data contains unexpected fields: {tuple(extra_fields)}")

    norm_data: dict[str, Any] = {}
    for field, is_required in field_requirements.items():
        if field not in filtered_data:
            if is_required:
                raise ValueError(f"{entity_name} data must contain a '{field}' field.")
        else:
            field_val = filtered_data[field]
            if isinstance(field_val, str):
                field_val = field_val.strip()
            if is_empty(field_val):
                if is_required:
                    raise ValueError(
                        f"'{field}' field of type {type(field_val).__name__} in {entity_name} data must not be empty."
                    )
                else:
                    continue
            norm_data[field] = field_val

    return norm_data


def base_normalization(
    data: dict[str, Any],
    data_spec: dict[str, Any],
    field_requirements: dict[str, bool],
    entity_name: str = "data",
) -> dict[str, Any]:
    assert (
        isinstance(data, dict)
        and isinstance(data_spec, dict)
        and isinstance(field_requirements, dict)
    )

    data_spec_field_set = set(data_spec.keys())
    field_requirements_field_set = set(field_requirements.keys())
    if data_spec_field_set != field_requirements_field_set:
        raise ValueError(
            "Data spec and field requirements must have the same set of fields. "
            f"Spec fields: {tuple(data_spec_field_set)}, requirements fields: {tuple(field_requirements_field_set)}"
        )

    filtered_data = filter_by_spec(data, data_spec)
    normalized_data = validate_normalize_fields(
        filtered_data=filtered_data,
        field_requirements=field_requirements,
        entity_name=entity_name,
    )
    return normalized_data


__all__ = [
    "filter_by_spec",
    "validate_normalize_fields",
    "base_normalization",
    "SpecFilterError",
    "InvalidSpecError",
    "SpecDataMismatchError",
    "SpecTypeError",
]
