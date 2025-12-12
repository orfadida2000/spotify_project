# Genius related constants
import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from lyricsgenius.genius import ResponseFormatT

from sp2genius.constants.path import ENV_DIR_PATH
from sp2genius.utils.path import is_file
from sp2genius.utils.typing import ReturnCode

GENIUS_TOKEN_ENV_VAR: Final[str] = "GENIUS_API_TOKEN"


_temp_path = Path(ENV_DIR_PATH / "genius.env")
_exit_code, _temp_path, _err = is_file(_temp_path)
if _exit_code != ReturnCode.SUCCESS or _temp_path is None:
    raise RuntimeError(f"Failed to find genius.env file: {_err}")

GENIUS_ENV_PATH: Final[Path] = _temp_path
BASE_DEV_API_URL: Final[str] = "https://api.genius.com"
BASE_PUB_API_URL: Final[str] = "https://genius.com/api"

MEDIA_SPECS: Final[dict[str, Any]] = {  # Only youTube are relevant for now
    "provider": str,
    "type": str,
    "url": str,
}
REQUIRED_MEDIA_FIELDS: Final[set[str]] = {
    "provider",
    "type",
    "url",
}

ARTIST_SPECS: Final[dict[str, Any]] = {
    "header_image_url": str,
    "id": int,
    "image_url": str,
    "name": str,
    "url": str,
}
REQUIRED_ARTIST_FIELDS: Final[set[str]] = {
    "id",
    "name",
    "url",
}

ALBUM_SPECS: Final[dict[str, Any]] = {
    "cover_art_url": str,
    "id": int,
    "name": str,
    "release_date_for_display": str,
    "url": str,
    "artist": ARTIST_SPECS,
}
REQUIRED_ALBUM_FIELDS: Final[set[str]] = {
    "id",
    "name",
    "release_date_for_display",
    "url",
    "artist",
}

SONG_SPECS: Final[dict[str, Any]] = {
    "header_image_thumbnail_url": str,
    "header_image_url": str,
    "id": int,
    "release_date_for_display": str,  # "August 27, 2009"
    "song_art_image_thumbnail_url": str,
    "song_art_image_url": str,
    "title": str,
    "url": str,
    "primary_artist": ARTIST_SPECS,
    "primary_artists": [ARTIST_SPECS],
    "featured_artists": [ARTIST_SPECS],
    "apple_music_id": str,
    "language": str,
    "album": ALBUM_SPECS,
    "media": [MEDIA_SPECS],
}
REQUIRED_SONG_FIELDS: Final[set[str]] = {
    "id",
    "release_date_for_display",
    "title",
    "url",
    "primary_artist",
    "album",
}


class ArtistSongsSort(StrEnum):
    TITLE = "title"
    POPULARITY = "popularity"
    RELEASE_DATE = "release_date"


DEFAULT_TEXT_FORMAT: Final[ResponseFormatT] = "plain"
MAX_PER_PAGE: Final[int] = 50
TIMEOUT: Final[int] = 10  # seconds

YOUTUBE_VIDEO_ID_RE: Final[re.Pattern[str]] = re.compile(pattern=r"[A-Za-z0-9_-]{11}")
YOUTUBE_VIDEO_URL_RE: Final[re.Pattern[str]] = re.compile(
    pattern=rf"^https://www.youtube.com/watch\?v=({YOUTUBE_VIDEO_ID_RE.pattern})$"
)
