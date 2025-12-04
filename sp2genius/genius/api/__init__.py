import os

from dotenv import load_dotenv

from .constants import GENIUS_ENV_PATH, GENIUS_TOKEN_ENV_VAR

load_dotenv(dotenv_path=GENIUS_ENV_PATH)
GENIUS_API_TOKEN = str(os.getenv(GENIUS_TOKEN_ENV_VAR))
if not GENIUS_API_TOKEN:
    raise OSError(
        "Missing Genius API token. "
        f"Please set the {GENIUS_TOKEN_ENV_VAR} environment variable in {GENIUS_ENV_PATH}."
    )
