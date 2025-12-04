from typing import Any

import requests

from . import CID, CSEC
from .constants import (
    AVAILABLE_MARKETS,
    BASE_API_URL,
    MAX_ALBUMS_PER_REQUEST,
    MAX_ARTISTS_PER_REQUEST,
    MAX_LIMIT,
    MAX_TRACKS_PER_REQUEST,
    SPOTIFY_ID_RE,
    TIMEOUT,
    ArtistIncludeGroups,
)
from .tokens import _get_token


def is_valid_spotify_id(spotify_id: str) -> bool:
    if not isinstance(spotify_id, str):
        return False
    return bool(SPOTIFY_ID_RE.fullmatch(spotify_id))


def is_valid_market(market: str) -> bool:
    return market in AVAILABLE_MARKETS


def _auth_headers() -> dict[str, str]:
    if not CID or not CSEC:
        raise ValueError("Client ID and Client Secret must be provided")
    try:
        token = _get_token(CID, CSEC)
    except Exception as e:
        raise ValueError(f"Spotify API authentication error: {e}") from None

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not params:
        params = None

    url = f"{BASE_API_URL}{path}"
    r = requests.get(url, headers=_auth_headers(), params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    return data


def get_markets() -> dict[str, Any]:
    path = "/markets"
    return _get(path)


def get_album(album_id: str, market: str | None = None) -> dict[str, Any]:
    if not is_valid_spotify_id(album_id):
        raise TypeError("album_id must be a valid Spotify ID")

    path = f"/albums/{album_id}"
    params = {}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_albums(album_ids: list[str], market: str | None = None) -> dict[str, Any]:
    if not isinstance(album_ids, list) or not all(is_valid_spotify_id(id_) for id_ in album_ids):
        raise TypeError("album_ids must be a list of valid Spotify IDs")
    if len(album_ids) == 0 or len(album_ids) > MAX_ALBUMS_PER_REQUEST:
        raise ValueError(f"album_ids list must contain between 1 and {MAX_ALBUMS_PER_REQUEST} IDs")

    path = "/albums"
    params = {"ids": ",".join(album_ids)}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_album_tracks(
    album_id: str,
    limit: int = MAX_LIMIT,
    offset: int = 0,
    market: str | None = None,
) -> dict[str, Any]:
    if not is_valid_spotify_id(album_id):
        raise TypeError("album_id must be a valid Spotify ID")
    if not isinstance(limit, int) or limit <= 0 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")

    path = f"/albums/{album_id}/tracks"
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_artist(artist_id: str) -> dict[str, Any]:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    path = f"/artists/{artist_id}"
    return _get(path)


def get_artists(artist_ids: list[str]) -> dict[str, Any]:
    if not isinstance(artist_ids, list) or not all(is_valid_spotify_id(id_) for id_ in artist_ids):
        raise TypeError("artist_ids must be a list of valid Spotify IDs")
    if len(artist_ids) == 0 or len(artist_ids) > MAX_ARTISTS_PER_REQUEST:
        raise ValueError(
            f"artist_ids list must contain between 1 and {MAX_ARTISTS_PER_REQUEST} IDs"
        )

    path = "/artists"
    params = {"ids": ",".join(artist_ids)}
    return _get(path, params)


def get_artist_albums(
    artist_id: str,
    include_groups: list[ArtistIncludeGroups | str] | None = None,
    limit: int = MAX_LIMIT,
    offset: int = 0,
    market: str | None = None,
) -> dict[str, Any]:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    if include_groups is None:
        include_groups = [
            ArtistIncludeGroups.ALBUM,
            ArtistIncludeGroups.SINGLE,
            ArtistIncludeGroups.COMPILATION,
        ]
    if not isinstance(include_groups, list) or len(include_groups) == 0:
        raise ValueError("include_groups must be a non-empty list")
    include_groups_set = set()
    for group in include_groups:
        if isinstance(group, ArtistIncludeGroups):
            include_groups_set.add(group.value)
        elif isinstance(group, str) and group.lower() in ArtistIncludeGroups._value2member_map_:
            include_groups_set.add(group.lower())
        else:
            raise ValueError(
                f"Invalid include_group: {group}. Must be one of {[g.value for g in ArtistIncludeGroups]}"
            )

    if not isinstance(limit, int) or limit <= 0 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")

    path = f"/artists/{artist_id}/albums"
    params = {
        "include_groups": ",".join(include_groups_set),
        "limit": limit,
        "offset": offset,
    }
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_artist_top_tracks(artist_id: str, market: str | None = None) -> dict[str, Any]:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    # url = f"{BASE_API_URL}/artists/{artist_id}/top-tracks"
    path = f"/artists/{artist_id}/top-tracks"
    params: dict[str, Any] = {}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_track(track_id: str, market: str | None = None) -> dict[str, Any]:
    if not is_valid_spotify_id(track_id):
        raise TypeError("track_id must be a valid Spotify ID")

    path = f"/tracks/{track_id}"
    params: dict[str, Any] = {}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)


def get_tracks(track_ids: list[str], market: str | None = None) -> dict[str, Any]:
    if not isinstance(track_ids, list) or not all(is_valid_spotify_id(id_) for id_ in track_ids):
        raise TypeError("track_ids must be a list of valid Spotify IDs")
    if len(track_ids) == 0 or len(track_ids) > MAX_TRACKS_PER_REQUEST:
        raise ValueError(f"track_ids list must contain between 1 and {MAX_TRACKS_PER_REQUEST} IDs")

    path = "/tracks"
    params: dict[str, Any] = {"ids": ",".join(track_ids)}
    if market is not None:
        if not is_valid_market(market):
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        params["market"] = market
    return _get(path, params)
