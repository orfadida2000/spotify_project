import argparse

from .constants import SPOTIFY_TRACK_URL_RE
from .extractors import extract_track_info
from .requests import (
    get_album,
    get_artists,
    get_track,
)


def track_url_to_tid(track_url: str) -> str:
    if not isinstance(track_url, str):
        raise TypeError("track_url must be a string")
    m = SPOTIFY_TRACK_URL_RE.fullmatch(track_url)
    if not m:
        raise ValueError("Invalid Spotify track URL format")
    return m.group(1)


def get_track_info(
    track_id: str,
    market: str | None = None,
    full_info: bool = False,
) -> dict:
    data = get_track(track_id, market)
    if full_info:
        album_id = data["album"]["id"]
        album = get_album(album_id, market)
        data["album"] = album

        artist_ids = [a["id"] for a in data["artists"]]
        artists = get_artists(artist_ids)["artists"]
        data["artists"] = artists
    track_info = extract_track_info(data)
    return track_info


def resolve_title_artists_from_spotify_url(url: str) -> tuple[str, list[str]]:
    tid = track_url_to_tid(url)
    track_info = get_track_info(tid, full_info=True)
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
        tid = track_url_to_tid(track_url=args.url)
        basic_track_info = get_track_info(track_id=tid, full_info=False)
        full_track_info = get_track_info(track_id=tid, full_info=True)
        import json

        with open("basic_track_info.json", "w") as f:
            json.dump(basic_track_info, f, indent=2)
        with open("full_track_info.json", "w") as f:
            json.dump(full_track_info, f, indent=2)
        print("Basic track info saved to 'basic_track_info.json'")
        print("Full track info saved to 'full_track_info.json'")
    except SystemExit:
        pass  # argparse already printed error message


if __name__ == "__main__":
    main()
