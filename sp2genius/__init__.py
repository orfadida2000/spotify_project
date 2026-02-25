from pathlib import Path
from typing import Final

from sp2genius.utils.path import ReturnCode, is_file

DEBUG_MODE: Final[bool] = False
SIMULATE_MODE: Final[bool] = False

_temp_path = Path(__file__)
_exit_code, _temp_path, _err = is_file(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to determine top package path: {_err}")
TOP_PKG_ABS_PATH: Final[Path] = _temp_path.parent
