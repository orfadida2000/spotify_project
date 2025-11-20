import re
from pathlib import Path
from typing import Final

from sp2genius.constants.paths import ENV_DIR_PATH
from sp2genius.utils.path import is_file
from sp2genius.utils.typing import ReturnCode

# Genius related constants
GENIUS_TOKEN_ENV_VAR: Final[str] = "GENIUS_API_TOKEN"

_temp_path = Path(ENV_DIR_PATH / "genius.env")
_exit_code, _temp_path, _err = is_file(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to find genius.env file: {_err}")
GENIUS_ENV_PATH: Final[Path] = _temp_path
BASE_API_URL: Final[str] = "https://api.genius.com"

GENIUS_LYRICS_URL_RE = re.compile(
    r"^https://genius\.com/[A-Za-z]+(?:-[A-Za-z]+)*-lyrics$"
)

__all__ = [
    "GENIUS_TOKEN_ENV_VAR",
    "GENIUS_ENV_PATH",
    "BASE_API_URL",
    "GENIUS_LYRICS_URL_RE"
]
