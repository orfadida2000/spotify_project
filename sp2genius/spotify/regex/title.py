import re
from typing import Final

from sp2genius.constants.text import EM_DASHES

_DASH_CLASS: Final[str] = "[" + re.escape(pattern="".join(EM_DASHES)) + "]"
# keywords used inside brackets or suffixes
_KW: Final[str] = (
    r"(?:feat\.?|ft\.?|live|remaster(?:ed)?|radio edit|single(?: version)?|version|"
    r"edit|mix|remix|acoustic|demo|instrumental|karaoke|bonus track|commentary|mono|"
    r"stereo|explicit|from\s+\"[^\"]+\"|from\s+the\s+.*|deluxe(?: edition)?)"
)

SPLIT_DASH_RE: Final[re.Pattern[str]] = re.compile(pattern=rf"\s*{_DASH_CLASS}\s*")
CUT_BRACKETED_KW_RE: Final[re.Pattern[str]] = re.compile(
    pattern=rf"[\(\[][^\)\]]*\b{_KW}\b[^\)\]]*[\)\]].*$", flags=re.I
)
REMIX_IN_BRACKETS_LEFT_RE: Final[re.Pattern[str]] = re.compile(
    pattern=r"[\(\[][^\)\]]*\bremix\b[^\)\]]*[\)\]]", flags=re.I
)
REMIX_ANY_RE: Final[re.Pattern[str]] = re.compile(pattern=r"\bremix\b", flags=re.I)

__all__ = [
    "SPLIT_DASH_RE",
    "CUT_BRACKETED_KW_RE",
    "REMIX_IN_BRACKETS_LEFT_RE",
    "REMIX_ANY_RE",
]
