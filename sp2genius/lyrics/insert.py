import argparse
from textwrap import dedent

import requests

from sp2genius.genius.constants import GENIUS_LYRICS_URL_RE

from .argparse import (
    general_url_normalization,
    spotify_track_uri,
    spotify_track_uri_to_url,
    spotify_track_url,
)
from .db import set_value_in_db


def fetch_follow_redirects(url: str) -> str:
    """
    Fetch URL with redirects allowed.
    Returns final URL as string.
    Raises ValueError on network error or bad status code.
    """
    try:
        resp = requests.get(url=url, timeout=5, allow_redirects=True)
    except requests.RequestException as e:
        raise ValueError(f"Network error: {e}") from None

    if resp.status_code != 200:
        raise ValueError(f"Server returned status {resp.status_code}")

    return resp.url  # final, canonical URL (Genius always lowercase)


def normalize_lyrics_url(url: str) -> str:
    """
    Normalize a Genius lyrics URL to the form 'https://genius.com/<first_part>-lyrics'.
    Returns the normalized URL if valid, else raises ValueError.
    """

    url = general_url_normalization(url)
    final_url = fetch_follow_redirects(url)

    # Must match the exact required structure
    if not bool(GENIUS_LYRICS_URL_RE.fullmatch(final_url)):
        raise ValueError(f"URL does not match Genius lyrics URL pattern: {final_url}")
    return final_url


def genius_lyrics_url(url: str) -> str:
    """
    Argparse type function: Genius lyrics URL
    Return 'https://genius.com/<first_part>-lyrics' if URL is a valid Genius lyrics URL.
    Otherwise raises argparse.ArgumentTypeError.
    """
    try:
        norm_url = normalize_lyrics_url(url)
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"--lyrics must be a valid Genius lyrics URL: {e}"
        ) from None
    return norm_url


def build_parser() -> argparse.ArgumentParser:
    desc = dedent("""\
    Provide a single Spotify track URL/URI and a matching Genius lyrics URL:

      1) --url SPOTIFY_TRACK_URL
         • A single Spotify track URL.
         • Must be a full URL, with or without scheme, may include query/fragment parts, host is case-insensitive.
         • A valid URL's host must be exactly "open.spotify.com" and path must start with "/track/" followed by a 22-character base62 track ID.
         • Example: --url "https://open.spotify.com/track/5UsLjwBaTHBX4ektWIr4XX"

      2) --uri SPOTIFY_TRACK_URI
         • A single Spotify track URI.
         • Must be of the form "spotify:track:<track_id>" where <track_id> is the 22-character base62 ID.
         • Will be treated case-sensitively.
         • Example: --uri "spotify:track:5UsLjwBaTHBX4ektWIr4XX"

      3) --lyrics GENIUS_LYRICS_URL
         • A single Genius lyrics URL.
         • Must be a full URL, with or without scheme, may include query/fragment parts, host is case-insensitive.
         • A valid URL is one that post redirection of a GET request to it is a valid URL to a  Genius lyrics web page. 
         • Example: --lyrics "https://genius.com/Eminem-not-afraid-lyrics"

    Notes:
      • Exactly one out of --url, --uri must be provided. 
      • --lyrics must be provided.
      • Use quotes for arguments that contain spaces, otherwise not needed.
    """)

    p = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawTextHelpFormatter,
        prog="Manual insertion",
    )
    g = p.add_mutually_exclusive_group(required=True)

    # -----------------------------------Mutually exclusive group-----------------------------------
    # Single-spec inputs
    g.add_argument(
        "--url",
        metavar="SPOTIFY_TRACK_URL",
        help="Full Spotify track URL (e.g., https://open.spotify.com/track/<track_id>).",
        type=spotify_track_url,
    )
    g.add_argument(
        "--uri",
        metavar="SPOTIFY_TRACK_URI",
        help="Spotify track URI (e.g., spotify:track:<track_id>).",
        type=spotify_track_uri,
    )
    # ----------------------------------------------------------------------------------------------

    p.add_argument(
        "--lyrics",
        metavar="GENIUS_LYRICS_URL",
        help="Full Genius lyrics URL (e.g., https://genius.com/Eminem-not-afraid-lyrics).",
        type=genius_lyrics_url,
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
        spotify_url = args.url if args.url else spotify_track_uri_to_url(args.uri)
        genius_url = args.lyrics
        set_value_in_db(spotify_url, genius_url)
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Success: {spotify_url} -> {genius_url}")


if __name__ == "__main__":
    main()
