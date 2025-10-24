from pathlib import Path
from typing import Final

import sp2genius

from .core import IS_A_SHELL

# Path constants
HOME: Final[Path] = Path.home() if IS_A_SHELL else (Path.home() / "tools" / "a-Shell")
ENV_DIR_PATH: Final[Path] = (HOME / "Documents" / ".secrets").resolve()
ABS_TOP_PKG_PATH: Final[Path] = sp2genius.ABS_TOP_PKG_PATH
ABS_ROOT_DIR_PATH: Final[Path] = ABS_TOP_PKG_PATH.parent
DB_PATH: Final[Path] = ABS_ROOT_DIR_PATH / "lyrics_db"

__all__ = [
    "HOME",
    "ENV_DIR_PATH",
    "ABS_TOP_PKG_PATH",
    "ABS_ROOT_DIR_PATH",
    "DB_PATH",
]
