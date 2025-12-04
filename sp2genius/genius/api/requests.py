from typing import Any

import requests

from . import GENIUS_API_TOKEN
from .constants import (
    BASE_DEV_API_URL,
    BASE_PUB_API_URL,
    DEFAULT_TEXT_FORMAT,
    MAX_PER_PAGE,
    TIMEOUT,
    ArtistSongsSort,
)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GENIUS_API_TOKEN}",
        "Accept": "application/json",
    }


def _get(
    path: str,
    params: dict[str, Any] | None = None,
    pub_api: bool = False,
) -> dict[str, Any]:
    if params is None:
        params = {}
    params.setdefault("text_format", DEFAULT_TEXT_FORMAT)

    url = f"{BASE_DEV_API_URL}{path}" if not pub_api else f"{BASE_PUB_API_URL}{path}"
    headers = _auth_headers() if not pub_api else None
    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    return data


# ---------- basic fetch by ID ----------


def get_song(song_id: int | str) -> dict[str, Any]:
    path = f"/songs/{song_id}"
    return _get(path)


def get_artist(artist_id: int | str) -> dict[str, Any]:
    path = f"/artists/{artist_id}"
    return _get(path)


def get_album(album_id: int | str) -> dict[str, Any]:
    path = f"/albums/{album_id}"
    return _get(path)


def get_artist_songs(
    artist_id: int | str,
    *,
    sort: ArtistSongsSort | str = ArtistSongsSort.TITLE,
    per_page: int = MAX_PER_PAGE,
    page_num: int = 1,
) -> dict[str, Any]:
    if isinstance(sort, str):
        if sort.lower() in ArtistSongsSort._value2member_map_:
            sort = ArtistSongsSort(sort.lower())
        else:
            raise ValueError(
                f"Invalid sort value: {sort}. Must be one of {[s.value for s in ArtistSongsSort]}"
            )
    elif not isinstance(sort, ArtistSongsSort):
        raise TypeError("sort must be an instance of ArtistSongsSort or a valid string")
    if not isinstance(per_page, int) or per_page <= 0 or per_page > MAX_PER_PAGE:
        raise ValueError(f"per_page must be an integer between 1 and {MAX_PER_PAGE}")
    if not isinstance(page_num, int) or page_num <= 0:
        raise ValueError("page_num must be a positive integer")

    path = f"/artists/{artist_id}/songs"
    params = {"sort": sort.value, "per_page": per_page, "page": page_num}
    return _get(path, params)


def get_artist_albums(
    artist_id: int | str,
    *,
    per_page: int = MAX_PER_PAGE,
    page_num: int = 1,
) -> dict[str, Any]:
    if not isinstance(per_page, int) or per_page <= 0 or per_page > MAX_PER_PAGE:
        raise ValueError(f"per_page must be an integer between 1 and {MAX_PER_PAGE}")
    if not isinstance(page_num, int) or page_num <= 0:
        raise ValueError("page_num must be a positive integer")

    path = f"/artists/{artist_id}/albums"
    params = {"per_page": per_page, "page": page_num}
    return _get(path, params, pub_api=True)


def get_album_tracks(
    album_id: int | str,
    *,
    per_page: int = MAX_PER_PAGE,
    page_num: int = 1,
) -> dict[str, Any]:
    if not isinstance(per_page, int) or per_page <= 0 or per_page > MAX_PER_PAGE:
        raise ValueError(f"per_page must be an integer between 1 and {MAX_PER_PAGE}")
    if not isinstance(page_num, int) or page_num <= 0:
        raise ValueError("page_num must be a positive integer")

    path = f"/albums/{album_id}/tracks"
    params = {"per_page": per_page, "page": page_num}
    return _get(path, params)
