from typing import Final

from ..utils import detect_host

HOST: Final[str] = detect_host()
if HOST == "Other":
    raise RuntimeError("Unsupported host environment detected")
IS_A_SHELL: Final[bool] = HOST == "a-Shell"

__all__ = [
    "HOST",
    "IS_A_SHELL",
]
