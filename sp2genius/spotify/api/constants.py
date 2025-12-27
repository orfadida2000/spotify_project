# Regular expressions for Spotify track identifiers
import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from sp2genius.constants.path import ENV_DIR_PATH
from sp2genius.utils.path import is_file
from sp2genius.utils.typing import ReturnCode

SPOTIFY_ID_RE: Final[re.Pattern[str]] = re.compile(pattern=r"[A-Za-z0-9]{22}")
SPOTIFY_TRACK_URL_RE: Final[re.Pattern[str]] = re.compile(
    pattern=f"^https://open.spotify.com/track/({SPOTIFY_ID_RE.pattern})$"
)
SPOTIFY_RELEASE_DATE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(pattern=r"^\d{4}$"),  # YYYY
    re.compile(pattern=r"^\d{4}-\d{2}$"),  # YYYY-MM
    re.compile(pattern=r"^\d{4}-\d{2}-\d{2}$"),  # YYYY-MM-DD
]

BASE_API_URL: Final[str] = "https://api.spotify.com/v1"
MAX_ALBUMS_PER_REQUEST: Final[int] = 20
MAX_LIMIT: Final[int] = 50
TIMEOUT: Final[int] = 10
AVAILABLE_MARKETS: Final[set[str]] = {
    "TW",
    "DZ",
    "PY",
    "CH",
    "DO",
    "HU",
    "BW",
    "SI",
    "FR",
    "AZ",
    "LY",
    "MK",
    "MV",
    "NA",
    "SK",
    "BG",
    "MH",
    "NZ",
    "AO",
    "AM",
    "PR",
    "SC",
    "DJ",
    "DM",
    "ES",
    "KZ",
    "ML",
    "GH",
    "ID",
    "HT",
    "GN",
    "BF",
    "AG",
    "SM",
    "NE",
    "BD",
    "KN",
    "KG",
    "US",
    "MA",
    "AE",
    "PK",
    "CI",
    "TN",
    "KE",
    "NO",
    "SE",
    "IL",
    "EE",
    "MU",
    "BO",
    "LS",
    "CV",
    "HK",
    "TR",
    "IQ",
    "LV",
    "LA",
    "VC",
    "TZ",
    "CD",
    "LU",
    "LC",
    "SA",
    "CZ",
    "VE",
    "SZ",
    "SL",
    "HN",
    "MZ",
    "BT",
    "EG",
    "PH",
    "CG",
    "TJ",
    "PE",
    "KW",
    "RO",
    "HR",
    "PT",
    "AD",
    "CL",
    "GR",
    "BE",
    "IN",
    "MO",
    "IS",
    "MW",
    "NR",
    "PG",
    "SN",
    "BN",
    "RW",
    "UG",
    "GB",
    "QA",
    "JP",
    "BZ",
    "NP",
    "GA",
    "WS",
    "UY",
    "XK",
    "SR",
    "MX",
    "PL",
    "IT",
    "ET",
    "DK",
    "TL",
    "TV",
    "CO",
    "BA",
    "ST",
    "FJ",
    "EC",
    "VN",
    "SB",
    "GW",
    "MY",
    "CR",
    "AT",
    "BJ",
    "TT",
    "IE",
    "MN",
    "BS",
    "MR",
    "BH",
    "LK",
    "CA",
    "KH",
    "AU",
    "RS",
    "TO",
    "TD",
    "FM",
    "FI",
    "CW",
    "BY",
    "GD",
    "DE",
    "ME",
    "GQ",
    "LI",
    "KI",
    "CM",
    "LB",
    "GY",
    "MC",
    "LR",
    "MD",
    "SG",
    "PS",
    "MG",
    "NL",
    "OM",
    "TH",
    "BB",
    "KR",
    "LT",
    "UA",
    "UZ",
    "GE",
    "VU",
    "BI",
    "MT",
    "PW",
    "ZW",
    "GT",
    "JM",
    "AR",
    "PA",
    "KM",
    "AL",
    "TG",
    "CY",
    "SV",
    "JO",
    "NG",
    "GM",
    "BR",
    "ZA",
    "NI",
    "ZM",
}

SP_AUTH: Final[str] = "https://accounts.spotify.com/api/token"
# Hidden cache file in the same directory as this module
_TOKEN_CACHE_PATH: Final[Path] = Path(__file__).resolve().parent / ".spotify_token_cache.json"
# Refresh a bit before the official expiry to be safe
_TOKEN_SAFETY_MARGIN: Final[int] = 60

SPOTIFY_ID_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_ID"
SPOTIFY_SECRET_ENV_VAR: Final[str] = "SPOTIFY_CLIENT_SECRET"

_temp_path = Path(ENV_DIR_PATH / "spotify.env")
_exit_code, _temp_path, _err = is_file(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to find spotify.env file: {_err}")
SPOTIFY_ENV_PATH: Final[Path] = _temp_path

SP_TRACK: Final[str] = "https://api.spotify.com/v1/tracks/{track_id}"
BASE_TRACK_URL: Final[str] = "https://open.spotify.com/track/{track_id}"

NONE_TYPE: Final[type] = type(None)


class ArtistIncludeGroups(StrEnum):
    ALBUM = "album"
    SINGLE = "single"
    APPEARS_ON = "appears_on"
    COMPILATION = "compilation"


IMAGE_SPECS: Final[dict[str, Any]] = {
    "url": str,
    "height": (int, NONE_TYPE),
    "width": (int, NONE_TYPE),
}
IMAGE_FIELD_REQUIREMENTS: Final[dict[str, bool]] = {
    "url": True,
    "height": False,
    "width": False,
}

ARTIST_SPECS: Final[dict[str, Any]] = {
    "followers": {"total": int},
    "genres": [str],
    "id": str,
    "images": [IMAGE_SPECS],
    "name": str,
    "popularity": int,
}
ARTIST_FIELD_REQUIREMENTS: Final[dict[str, bool]] = {
    "followers": False,
    "genres": False,
    "id": True,
    "images": False,
    "name": True,
    "popularity": False,
}

ALBUM_SPECS: Final[dict[str, Any]] = {
    "album_type": str,
    "total_tracks": int,
    "id": str,
    "images": [IMAGE_SPECS],
    "name": str,
    "release_date": str,
    "artists": [ARTIST_SPECS],
    "label": str,
    "popularity": int,
}
ALBUM_FIELD_REQUIREMENTS: Final[dict[str, bool]] = {
    "album_type": True,
    "total_tracks": True,
    "id": True,
    "images": False,
    "name": True,
    "release_date": True,
    "artists": True,
    "label": False,
    "popularity": False,
}

TRACK_SPECS: Final[dict[str, Any]] = {
    "album": ALBUM_SPECS,
    "artists": [ARTIST_SPECS],
    "disc_number": int,
    "duration_ms": int,
    "explicit": bool,
    "id": str,
    "name": str,
    "popularity": int,
    "track_number": int,
}
TRACK_FIELD_REQUIREMENTS: Final[dict[str, bool]] = {
    "album": True,
    "artists": True,
    "disc_number": True,
    "duration_ms": True,
    "explicit": True,
    "id": True,
    "name": True,
    "popularity": False,
    "track_number": True,
}
