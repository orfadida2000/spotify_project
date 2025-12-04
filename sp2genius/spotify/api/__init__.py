import os

from dotenv import load_dotenv

from .constants import (
    SPOTIFY_ENV_PATH,
    SPOTIFY_ID_ENV_VAR,
    SPOTIFY_SECRET_ENV_VAR,
)

load_dotenv(dotenv_path=SPOTIFY_ENV_PATH)
CID = str(os.getenv(SPOTIFY_ID_ENV_VAR))
CSEC = str(os.getenv(SPOTIFY_SECRET_ENV_VAR))
if not CID or not CSEC:
    raise OSError(
        "Missing Spotify API credentials. "
        f"Please set the {SPOTIFY_ID_ENV_VAR} and {SPOTIFY_SECRET_ENV_VAR} environment variables in {SPOTIFY_ENV_PATH}."
    )
