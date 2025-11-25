import re
from typing import Final

# Regular expressions for Spotify track identifiers
_TRACK_ID_RE: Final[str] = r"[A-Za-z0-9]{22}"

TRACK_URL_RE: Final[re.Pattern[str]] = re.compile(
    pattern=r"^(?:https?://)?"  # optional scheme
    r"open\.spotify\.com"  # exact host
    r"/track/"  # path
    rf"({_TRACK_ID_RE})"  # 22-char base62 track id
    r"(?:[/?#].*)?$",  # optional extras (query/fragment/trailing slash)
    flags=re.I,
)
TRACK_URI_RE: Final[re.Pattern[str]] = re.compile(pattern=rf"^spotify:track:{_TRACK_ID_RE}$")

__all__ = [
    "TRACK_URL_RE",
    "TRACK_URI_RE",
]
