from pathlib import Path
from typing import Final

from sp2genius.constants.paths import ENV_DIR_PATH
from sp2genius.utils.path import is_file
from sp2genius.utils.typing import ReturnCode

# Spotify related constants
CHARTS_URL: Final[str] = "https://kworb.net/spotify/listeners.html"
SPOTIFY_ID_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_ID"
SPOTIFY_SECRET_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_SECRET"

_temp_path = Path(ENV_DIR_PATH / "spotify.env")
_exit_code, _temp_path, _err = is_file(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to find spotify.env file: {_err}")
SPOTIFY_ENV_PATH: Final[Path] = _temp_path

SP_AUTH: Final[str] = "https://accounts.spotify.com/api/token"
SP_TRACK: Final[str] = "https://api.spotify.com/v1/tracks/{track_id}"
BASE_TRACK_URL: Final[str] = "https://open.spotify.com/track/{track_id}"

__all__ = (
    "CHARTS_URL",
    "SPOTIFY_ID_ENV_VAR",
    "SPOTIFY_SECRET_ENV_VAR",
    "SPOTIFY_ENV_PATH",
    "SP_AUTH",
    "SP_TRACK",
    "BASE_TRACK_URL",
)
