from .genius.tables import TABLES as GENIUS_TABLES
from .spotify.tables import TABLES as SPOTIFY_TABLES

FULL_TABLES = GENIUS_TABLES + SPOTIFY_TABLES
FULL_SCHEMA = "\n".join(FULL_TABLES)
