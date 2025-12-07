from typing import Any

from sp2genius.utils.specfilter import filter_by_spec

from .constants import SONG_SPECS
from .normalization import normalize_song
from .requests import get_song, get_song_by_title_artist


def get_song_info(
    identifier: int | str | dict[str, str | list[str]],
    by_id: bool = False,
) -> dict[str, Any]:
    if by_id:
        if not isinstance(identifier, (int, str)):
            raise ValueError("Identifier must be an int or str when by_id is True.")
        song = get_song(song_id=identifier)["song"]
    else:
        if not isinstance(identifier, dict):
            raise ValueError("Identifier must be a dict when by_id is False.")
        title = identifier.get("title", "")
        artist_lst = identifier.get("artist_lst", [])
        song = get_song_by_title_artist(title, artist_lst)  # type: ignore
    filtered_song = filter_by_spec(song, SONG_SPECS)
    normalized_song = normalize_song(filtered_song)
    return normalized_song


def genius_url_for_title_artists(
    title: str,
    artist_lst: list[str],
) -> str:
    song_info = get_song_info(
        identifier={
            "title": title,
            "artist_lst": artist_lst,
        },
        by_id=False,
    )
    url = song_info.get("url", "").strip()
    if not url:
        raise ValueError("Could not retrieve Genius URL for the given title and artists.")
    return url
