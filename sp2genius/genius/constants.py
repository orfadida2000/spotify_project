import re

GENIUS_LYRICS_URL_RE = re.compile(r"^https://genius\.com/[A-Za-z]+(?:-[A-Za-z]+)*-lyrics$")


__all__ = [
    "GENIUS_LYRICS_URL_RE",
]
