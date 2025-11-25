import argparse

import requests

from . import CID, CSEC
from .extractors import extract_track_info
from .requests import (
    build_album_api_request,
    build_artists_api_request,
    build_track_api_request,
    track_url_to_tid,
)
from .tokens import _get_token


def add_request_headers(req: dict, token: str) -> None:
    """Add Authorization header to a Spotify API request dictionary."""
    headers = req.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    req["headers"] = headers


def make_request(req: dict, client_id: str, client_secret: str) -> dict:
    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret must be provided")
    try:
        token = _get_token(client_id, client_secret)
    except Exception as e:
        raise ValueError(f"Spotify API authentication error: {e}") from None
    add_request_headers(req, token)
    resp = requests.get(**req)
    resp.raise_for_status()
    data = resp.json()
    return data


def get_track_info(
    track_id: str,
    client_id: str = CID,
    client_secret: str = CSEC,
    full_info: bool = False,
) -> dict:
    req = build_track_api_request(track_id)
    data = make_request(req, client_id, client_secret)
    if full_info:
        album_id = data["album"]["id"]
        album_req = build_album_api_request(album_id)
        album = make_request(album_req, client_id, client_secret)
        data["album"] = album

        artist_ids = [a["id"] for a in data["artists"]]
        artists_req = build_artists_api_request(artist_ids)
        artists = make_request(artists_req, client_id, client_secret)["artists"]
        data["artists"] = artists
    track_info = extract_track_info(data)
    return track_info


def resolve_title_artists_from_spotify_url(
    url: str,
    client_id: str = CID,
    client_secret: str = CSEC,
) -> tuple[str, list[str]]:
    tid = track_url_to_tid(url)
    track_info = get_track_info(tid, client_id, client_secret, full_info=True)
    title = track_info["title"]
    artist_lst = [track_info["primary_artist"]["name"]] + [
        artist["name"] for artist in track_info["featured_artists"]
    ]
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
        args = parse_args()
        title, artist = resolve_title_artists_from_spotify_url(args.url)
        print(f"Title: {title}")
        print(f"Artist list: {artist}")
    except SystemExit:
        pass  # argparse already printed error message


if __name__ == "__main__":
    main()
