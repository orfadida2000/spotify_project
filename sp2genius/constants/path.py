from pathlib import Path
from typing import Final

from sp2genius import TOP_PKG_ABS_PATH
from sp2genius.utils.path import is_dir
from sp2genius.utils.typing import ReturnCode

from .core import IS_A_SHELL

# Private variables for path constants definition
_temp_path: Path | None = None
_exit_code: ReturnCode = ReturnCode.NOT_FOUND
_err: str = ""

# Path constants
_temp_path = Path.home() if IS_A_SHELL else (Path.home() / "tools" / "a-Shell")
_exit_code, _temp_path, _err = is_dir(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to determine platform dependent home directory: {_err}")
HOME_PATH: Final[Path] = _temp_path

_temp_path = HOME_PATH / "Documents" / ".secrets"
_exit_code, _temp_path, _err = is_dir(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to determine environment directory path: {_err}")
ENV_DIR_PATH: Final[Path] = _temp_path

ROOT_DIR_PATH: Final[Path] = TOP_PKG_ABS_PATH.parent


__all__ = [
    "HOME_PATH",
    "ENV_DIR_PATH",
    "ROOT_DIR_PATH",
]
