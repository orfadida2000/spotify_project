from typing import Any

from .normalization import normalize_album, normalize_artist, normalize_song
from .requests import get_album, get_artist, get_song, get_song_by_title_artist


def get_song_info_by_id(song_id: int | str) -> dict[str, Any]:
    assert isinstance(song_id, (int, str))
    song = get_song(song_id=song_id)["song"]
    normalized_song = normalize_song(song_data=song, is_filtered=False)
    return normalized_song


def get_song_info_by_title_artist(
    title: str,
    artist_lst: list[str] | None = None,
) -> dict[str, Any]:
    if artist_lst is None:
        artist_lst = []
    assert (
        isinstance(title, str)
        and isinstance(artist_lst, list)
        and all(isinstance(artist, str) for artist in artist_lst)
    )
    song = get_song_by_title_artist(title, artist_lst)
    normalized_song = normalize_song(song_data=song, is_filtered=False)
    return normalized_song


def get_album_info_by_id(album_id: int | str) -> dict[str, Any]:
    assert isinstance(album_id, (int, str))
    album = get_album(album_id=album_id)["album"]
    normalized_album = normalize_album(album_data=album, is_filtered=False)
    return normalized_album


def get_artist_info_by_id(artist_id: int | str) -> dict[str, Any]:
    assert isinstance(artist_id, (int, str))
    artist = get_artist(artist_id=artist_id)["artist"]
    normalized_artist = normalize_artist(artist_data=artist, is_filtered=False)
    return normalized_artist


def genius_url_for_title_artists(
    title: str,
    artist_lst: list[str] | None = None,
) -> str:
    song_info = get_song_info_by_title_artist(title=title, artist_lst=artist_lst)
    url = song_info.get("url", "").strip()
    if not url:
        raise ValueError("Could not retrieve Genius URL for the given title and artists.")
    return url
