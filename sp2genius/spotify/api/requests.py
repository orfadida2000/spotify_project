from .constants import (
    AVAILABLE_MARKETS,
    BASE_API_URL,
    INCLUDE_GROUPS,
    MAX_ALBUMS_PER_REQUEST,
    MAX_ARTISTS_PER_REQUEST,
    MAX_LIMIT,
    MAX_TRACKS_PER_REQUEST,
    SPOTIFY_ID_RE,
    SPOTIFY_TRACK_URL_RE,
    TIMEOUT,
)


def is_valid_spotify_id(spotify_id: str) -> bool:
    if not isinstance(spotify_id, str):
        return False
    return bool(SPOTIFY_ID_RE.fullmatch(spotify_id))


def track_url_to_tid(track_url: str) -> str:
    if not isinstance(track_url, str):
        raise TypeError("track_url must be a string")
    m = SPOTIFY_TRACK_URL_RE.fullmatch(track_url)
    if not m:
        raise ValueError("Invalid Spotify track URL format")
    return m.group(1)


def _build_markets_api_request() -> dict:
    return {
        "url": f"{BASE_API_URL}/markets",
        "timeout": TIMEOUT,
    }


def build_album_api_request(album_id: str, market: str | None = None) -> dict:
    if not is_valid_spotify_id(album_id):
        raise TypeError("album_id must be a valid Spotify ID")
    req: dict = {
        "url": f"{BASE_API_URL}/albums/{album_id}",
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"] = {"market": market}
    return req


def build_albums_api_request(album_ids: list[str], market: str | None = None) -> dict:
    if not isinstance(album_ids, list) or not all(is_valid_spotify_id(id_) for id_ in album_ids):
        raise TypeError("album_ids must be a list of valid Spotify IDs")
    if len(album_ids) == 0 or len(album_ids) > MAX_ALBUMS_PER_REQUEST:
        raise ValueError(f"album_ids list must contain between 1 and {MAX_ALBUMS_PER_REQUEST} IDs")
    if len(album_ids) == 1:
        return build_album_api_request(album_ids[0], market)
    req: dict = {
        "url": f"{BASE_API_URL}/albums",
        "params": {"ids": ",".join(album_ids)},
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"]["market"] = market
    return req


def build_album_tracks_api_request(
    album_id: str,
    limit: int = 50,
    offset: int = 0,
    market: str | None = None,
) -> dict:
    if not is_valid_spotify_id(album_id):
        raise TypeError("album_id must be a valid Spotify ID")
    if not isinstance(limit, int) or limit <= 0 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    req = {
        "url": f"{BASE_API_URL}/albums/{album_id}/tracks",
        "params": {"limit": limit, "offset": offset},
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"]["market"] = market
    return req


def build_artist_api_request(artist_id: str) -> dict:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    req = {
        "url": f"{BASE_API_URL}/artists/{artist_id}",
        "timeout": TIMEOUT,
    }
    return req


def build_artists_api_request(artist_ids: list[str]) -> dict:
    if not isinstance(artist_ids, list) or not all(is_valid_spotify_id(id_) for id_ in artist_ids):
        raise TypeError("artist_ids must be a list of valid Spotify IDs")
    if len(artist_ids) == 0 or len(artist_ids) > MAX_ARTISTS_PER_REQUEST:
        raise ValueError(
            f"artist_ids list must contain between 1 and {MAX_ARTISTS_PER_REQUEST} IDs"
        )
    if len(artist_ids) == 1:
        return build_artist_api_request(artist_ids[0])
    req = {
        "url": f"{BASE_API_URL}/artists",
        "params": {"ids": ",".join(artist_ids)},
        "timeout": TIMEOUT,
    }
    return req


def build_artist_albums_api_request(
    artist_id: str,
    include_groups: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
    market: str | None = None,
) -> dict:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    if include_groups is None:
        include_groups = ["album", "single", "compilation"]
    if (
        not isinstance(include_groups, list)
        or not all(group in INCLUDE_GROUPS for group in include_groups)
        or len(include_groups) == 0
    ):
        raise ValueError(
            f"include_groups must be a non-empty list containing any of the following: {INCLUDE_GROUPS}"
        )
    if not isinstance(limit, int) or limit <= 0 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    req = {
        "url": f"{BASE_API_URL}/artists/{artist_id}/albums",
        "params": {
            "include_groups": ",".join(include_groups),
            "limit": limit,
            "offset": offset,
        },
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"]["market"] = market
    return req


def build_artist_top_tracks_api_request(artist_id: str, market: str | None = None) -> dict:
    if not is_valid_spotify_id(artist_id):
        raise TypeError("artist_id must be a valid Spotify ID")
    # url = f"{BASE_API_URL}/artists/{artist_id}/top-tracks"
    req = {
        "url": f"{BASE_API_URL}/artists/{artist_id}/top-tracks",
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"] = {"market": market}
    return req


def build_track_api_request(track_id: str, market: str | None = None) -> dict:
    if not is_valid_spotify_id(track_id):
        raise TypeError("track_id must be a valid Spotify ID")
    req = {
        "url": f"{BASE_API_URL}/tracks/{track_id}",
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"] = {"market": market}
    return req


def build_tracks_api_request(track_ids: list[str], market: str | None = None) -> dict:
    if not isinstance(track_ids, list) or not all(is_valid_spotify_id(id_) for id_ in track_ids):
        raise TypeError("track_ids must be a list of valid Spotify IDs")
    if len(track_ids) == 0 or len(track_ids) > MAX_TRACKS_PER_REQUEST:
        raise ValueError(f"track_ids list must contain between 1 and {MAX_TRACKS_PER_REQUEST} IDs")
    if len(track_ids) == 1:
        return build_track_api_request(track_ids[0], market)
    req = {
        "url": f"{BASE_API_URL}/tracks",
        "params": {"ids": ",".join(track_ids)},
        "timeout": TIMEOUT,
    }
    if market is not None:
        if market not in AVAILABLE_MARKETS:
            raise ValueError(f"market must be one of the available markets: {AVAILABLE_MARKETS}")
        req["params"]["market"] = market
    return req
