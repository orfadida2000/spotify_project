import keyword


def is_valid_py_identifier(name: object) -> int:
    """
    Check if a string is a valid Python identifier.
    Returns an integer code indicating the result.

    Args:
        name: The string to check.

    Returns: (int)
        0 if valid identifier,
        1 if not a string,
        2 if empty string,
        3 if not a valid identifier,
        4 if a Python keyword.
        5 if a dunder identifier.
    """
    if not isinstance(name, str):
        return 1
    if not name:
        return 2
    if not name.isidentifier():
        return 3
    if keyword.iskeyword(name):
        return 4
    if is_dunder_identifier(name):
        return 5
    return 0


def is_dunder_identifier(identifier: str) -> bool:
    """
    Check if a python identifier string is also a "dunder" (double underscore) identifier.

    Args:
        identifier: A valid python identifier string.

    Returns: (bool)
        True if the python identifier string is also a dunder identifier, False otherwise.
    """
    if not isinstance(identifier, str):
        raise TypeError(f"identifier must be str, got: {type(identifier)}")

    # Reject identifiers that are too short to be dunder (including "____")
    if len(identifier) < 5:
        return False

    # At this point we know len(identifier) >= 5 so the 2 chars prefix and suffix are not overlapping
    # Rejects identifiers that do not start and end with double underscores
    if not identifier.startswith("__") or not identifier.endswith("__"):
        return False

    # At this point we know len(identifier) >= 5 so we can safely slice the inner part
    # Also, since len(identifier) >= 5, inner part cannot be empty
    inner = identifier[2:-2]

    # Rejects identifiers that have only underscores in the inner part
    if all(c == "_" for c in inner):
        return False

    # At this point we know inner has at least one valid non-underscore character
    # (validity of this 1 char is assumed because the whole identifier argument is assumed to be a valid python identifier)
    # Rejects identifiers that start or end with an underscore in the inner part
    # (i.e. identifiers that don't start and end with exactly two underscores)
    if inner.startswith("_") or inner.endswith("_"):
        return False

    return True
