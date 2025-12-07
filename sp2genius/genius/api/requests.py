from typing import Any

import requests
from lyricsgenius import Genius

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

    return data["response"]


# ---------- basic fetch by ID from the native Genius API ----------


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


# ---------- complex fetch by title, artist from lyricsgenius API ----------


def get_song_by_title_artist(title: str, artist_lst: list[str]) -> dict[str, Any]:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Title must be a non-empty string.")
    if not isinstance(artist_lst, list):
        raise ValueError("Artist must be a list of strings.")

    # Clean title and artist list
    title = title.strip()
    artist_lst = [
        artist.strip() for artist in artist_lst if isinstance(artist, str) and artist.strip()
    ]

    song = None
    if not GENIUS_API_TOKEN or not title:
        raise ValueError("Missing Genius API token or empty title.")
    g = Genius(
        access_token=GENIUS_API_TOKEN,
        timeout=TIMEOUT,
        skip_non_songs=True,
        remove_section_headers=False,
        response_format=DEFAULT_TEXT_FORMAT,
    )
    if len(artist_lst) == 0:
        song = g.search_song(title=title, get_full_info=True)
    else:
        for artist in artist_lst:
            song = g.search_song(title=title, artist=artist, get_full_info=True)
            if song:
                break
    if not song:
        raise ValueError("404 could not find song URL on Genius.")
    data = song.to_dict()  # type: ignore
    return data
