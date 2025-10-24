from pathlib import Path
from typing import Final

from .paths import ENV_DIR_PATH

# Spotify related constants
CHARTS_URL: Final[str] = "https://kworb.net/spotify/listeners.html"
SPOTIFY_ID_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_ID"
SPOTIFY_SECRET_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_SECRET"
SPOTIFY_ENV_PATH: Final[Path] = (ENV_DIR_PATH / "spotify.env").resolve()
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
