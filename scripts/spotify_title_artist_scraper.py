import argparse
import base64
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

IS_A_SHELL = False
HOME = Path.home() if IS_A_SHELL else (Path.home() / "tools" / "a-Shell")
ENV_PATH = (HOME / "Documents" / ".secrets" / "spotify.env").resolve()
load_dotenv(ENV_PATH)

CID = os.getenv("SPOTIFY_CLIENT_ID")
CSEC = os.getenv("SPOTIFY_CLIENT_SECRET")

SP_AUTH = "https://accounts.spotify.com/api/token"
SP_TRACK = "https://api.spotify.com/v1/tracks/{}"

_TRACK_ID_RE = r"[A-Za-z0-9]{22}"
_VALID_TRACK_URL_RE = re.compile(
    rf"^https://open\.spotify\.com/track/({_TRACK_ID_RE})(?:[/?#].*)?$",
    re.IGNORECASE,
)

_DEBUG_MODE = False


def _extract_track_id(url: str, normalized: bool) -> str | None:
    """
    Extract the 22-character case-sensitive Spotify track ID from a Spotify track URL.
    Returns the track ID if found, else raises ValueError.

    Notes:
        • Assumes the URL has been validated as a Spotify track URL.
        • Assumes the url is normalized if normalized=True (i.e., the track ID is the only part after the last slash).
        • If normalized=False, the function will still work for non-normalized URLs but may be less efficient.
        • Valid track ID characters: A-Z, a-z, 0-9.
        • Valid track ID example: 3n3Ppam7vgaVa1iaRUc9Lp
        • Valid URL: https://open.spotify.com/track/{track_id}
    """
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip()
    if normalized:
        # url is non-empty, so rsplit always returns at least one element
        track_id = url.rsplit("/", 1)[-1]
        return track_id
    m = _VALID_TRACK_URL_RE.fullmatch(url)
    if not m:
        return None
    return m.group(1)


def _get_token(client_id: str, client_secret: str) -> str:
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        SP_AUTH,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _print_recursive_dict(data: dict, indent: int = 0, ignore_keys: set[str] | None = None) -> None:
    """
    Recursively prints a dictionary, handling nested dictionaries and lists.
    """
    if ignore_keys is None:
        ignore_keys = set()
    indent_space = "  " * indent
    if isinstance(data, dict):
        print(f"{indent_space}{{")
        for key, value in data.items():
            if key in ignore_keys:
                continue
            print(f"{indent_space}  '{key}': ", end="")
            _print_recursive_dict(data=value, indent=indent + 1, ignore_keys=ignore_keys)
        print(f"{indent_space}}},")
    elif isinstance(data, list):
        print(f"{indent_space}[")
        for item in data:
            print(f"{indent_space}  ", end="")
            _print_recursive_dict(data=item, indent=indent + 1, ignore_keys=ignore_keys)
        print(f"{indent_space}],")
    else:
        print(f"{data},")


def _debug_response_data(data: dict) -> None:
    print("Full response data:")
    _print_recursive_dict(data=data, indent=0, ignore_keys={"available_markets"})
    print()


def resolve_title_artists_from_spotify_url(
    url: str,
    client_id: str | None = CID,
    client_secret: str | None = CSEC,
    is_url_normalized: bool = True,
) -> tuple[str, list[str]]:
    if not client_id or not client_secret:
        print("Client ID and Client Secret must be provided")
        return "", []
    tid = _extract_track_id(url, normalized=is_url_normalized)
    if not tid:
        return "", []
    token = _get_token(client_id, client_secret)
    resp = requests.get(
        SP_TRACK.format(tid),
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    global _DEBUG_MODE
    if _DEBUG_MODE:
        _debug_response_data(data)
    title = data.get("name", "")
    artist_lst = [a["name"] for a in data.get("artists", []) if "name" in a]
    return title, artist_lst


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert Spotify track URL to song title and artist name(s).",
        prog="song_info_from_spotify_url",
    )

    p.add_argument(
        "--url",
        metavar="SPOTIFY_TRACK_URL",
        help="Full Spotify track URL (e.g., https://open.spotify.com/track/<track_id>).",
        type=str,
        required=True,
    )

    return p


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()
    return args


def main():
    try:
        global _DEBUG_MODE
        _DEBUG_MODE = True
        args = parse_args()
        title, artist = resolve_title_artists_from_spotify_url(args.url, is_url_normalized=False)
        print(f"Title: {title}")
        print(f"Artist list: {artist}")
    except SystemExit:
        pass  # argparse already printed error message
    _DEBUG_MODE = False


if __name__ == "__main__":
    main()
