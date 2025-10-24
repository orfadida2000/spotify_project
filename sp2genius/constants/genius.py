from .paths import ENV_DIR_PATH

# Genius related constants
GENIUS_TOKEN_ENV_VAR = "GENIUS_API_TOKEN"
GENIUS_ENV_PATH = (ENV_DIR_PATH / "genius.env").resolve()

__all__ = [
    "GENIUS_TOKEN_ENV_VAR",
    "GENIUS_ENV_PATH",
]
