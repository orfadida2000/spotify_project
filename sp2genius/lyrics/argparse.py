import argparse
import re
from pathlib import Path
from textwrap import dedent

from validators import url as is_valid_url

from sp2genius.spotify.constants import BASE_TRACK_URL
from sp2genius.spotify.regex.title import (
    CUT_BRACKETED_KW_RE,
    REMIX_ANY_RE,
    REMIX_IN_BRACKETS_LEFT_RE,
    SPLIT_DASH_RE,
)
from sp2genius.spotify.regex.url import TRACK_URI_RE, TRACK_URL_RE
from sp2genius.utils.path import is_readable_file


def general_url_normalization(url: str) -> str:
    """
    Normalize, trim.
    Validate:
    - not empty
    - scheme https
    - no IPv4
    - no IPv6
    - no port
    - syntactically valid URL
    If scheme is missing, assumes https.
    Returns cleaned URL or raises ValueError.
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string")

    url = url.strip()
    if not url:
        raise ValueError("URL is an empty string")
    if url.find("://") == -1:
        url = f"https://{url}"

    valid = is_valid_url(
        url,
        skip_ipv6_addr=True,
        skip_ipv4_addr=True,
        may_have_port=False,
        validate_scheme=lambda s: s == "https",
    )

    if not valid:
        raise ValueError(f"URL is not valid: {valid}")

    return url


def clean_title_for_genius(s: str) -> str:
    parts = SPLIT_DASH_RE.split(s, maxsplit=1)
    left = parts[0]
    right = parts[1] if len(parts) > 1 else ""

    remix_left = bool(REMIX_IN_BRACKETS_LEFT_RE.search(left))
    remix_right = bool(REMIX_ANY_RE.search(right))

    left = CUT_BRACKETED_KW_RE.sub("", left)
    title = re.sub(pattern=r"\s{2,}", repl=" ", string=left).strip()

    if remix_left or remix_right:
        title += " (Remix)"
    return title


def normalize_track_url(url: str) -> str:
    """
    Normalize a Spotify track URL to the form 'https://open.spotify.com/track/<track_id>'.
    Accepts URLs with or without scheme and with optional query/fragment.
    Returns the normalized URL if valid, else raises ValueError.
    """
    url = general_url_normalization(url)
    m = TRACK_URL_RE.fullmatch(url)
    if not m:
        raise ValueError(f"URL is not a valid Spotify track URL: {url}")
    track_id = m.group(1)
    return BASE_TRACK_URL.format(track_id=track_id)


def spotify_track_url(url: str) -> str:
    """
    Argparse type function: Spotify track URL
    Return 'https://open.spotify.com/track/<track_id>' if URL is a valid Spotify track URL.
    Accepts with or without scheme and with optional query/fragment.
    Otherwise raises argparse.ArgumentTypeError.
    """
    try:
        norm_url = normalize_track_url(url)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--url must be a valid Spotify track URL: {e}") from None
    return norm_url


def normalize_track_uri(uri: str) -> str:
    """
    Normalize a Spotify track URI to the form 'spotify:track:<track_id>'.
    Returns the normalized URI if valid, else raises ValueError.
    """
    uri = uri.strip()
    m = TRACK_URI_RE.fullmatch(uri)
    if not m:
        raise ValueError(f"URI is not a valid Spotify track URI: {uri}")
    return uri


def spotify_track_uri(uri: str) -> str:
    """
    Argparse type function: Spotify track URI
    Return 'spotify:track:<track_id>' if URI is a valid Spotify track URI.
    Otherwise raises argparse.ArgumentTypeError.
    """
    try:
        norm_uri = normalize_track_uri(uri)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--uri must be a valid Spotify track URI: {e}") from None
    return norm_uri


def spotify_track_uri_to_url(uri: str) -> str:
    """
    Convert a Spotify track URI (spotify:track:<id>) to a full URL (https://open.spotify.com/track/<id>).
    Assumes the input is a valid URI; does not validate format, only that it's non-empty after stripping (raises ValueError if empty).
    """
    uri = uri.strip()
    if not uri:
        raise ValueError("Empty URI provided.")
    track_id = uri.rsplit(sep=":", maxsplit=1)[-1]
    return BASE_TRACK_URL.format(track_id=track_id)


def normalize_song_title(title: str) -> str:
    """
    Normalize a song title by stripping leading/trailing whitespace.
    Returns the stripped title if non-empty, else raises ValueError.
    """
    title = title.strip()
    if not title:
        raise ValueError("Empty title provided.")
    title = clean_title_for_genius(title)
    if not title:
        raise ValueError("Title is empty after cleaning.")
    return title


def song_title(title: str) -> str:
    """
    Argparse type function: Song title
    Strip leading/trailing whitespace and ensure not empty.
    Return stripped string if non empty.
    Otherwise raise argparse.ArgumentTypeError.
    """
    try:
        norm_title = normalize_song_title(title)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--title must be a non-empty string: {e}") from None
    return norm_title


def normalize_artist_list(artists: str) -> list[str]:
    """
    Normalize a comma-separated list of artist names.
    Split by commas, strip whitespace, only non-empty names.
    Return list of stripped names or an empty list if there are none.
    """
    artists = artists.strip()
    artist_lst = [a.strip() for a in artists.split(",") if a.strip()]
    return artist_lst


def artist_list(artists: str) -> list[str]:
    """
    Argparse type function: Comma-separated list of artist names
    Split by commas, strip whitespace, only non-empty names.
    Return list of stripped names or an empty list if there are none.
    """
    artist_lst = normalize_artist_list(artists)
    return artist_lst


def readable_file(path: str) -> Path:
    """
    Argparse type function: Readable file path
    Ensure the path exists and is a readable file.
    Return the path as a Path object if valid.
    Otherwise raise argparse.ArgumentTypeError.
    """
    is_readable, p, err = is_readable_file(path)
    if not is_readable or p is None:
        raise argparse.ArgumentTypeError(f"--batch must be a readable file: {err}")
    return p


def build_parser() -> argparse.ArgumentParser:
    desc = dedent("""\
    Provide a single song spec or a batch file of many:

      1) --title TITLE and an optional --artist ARTIST[,ARTIST,...]
         • Use quotes if a title or artist contains spaces, otherwise not needed.
         • Artists are separated by commas.
         • Specify only the primary artist(s) first.
         • Only when --title is given, --artist will be meaningful, otherwise ignored.
         • --artist may be omitted if only the title is known.
         • Example: --title "Bohemian Rhapsody" --artist Queen

      2) --url SPOTIFY_TRACK_URL
         • A single Spotify track URL.
         • Must be a full URL, with or without scheme, may include query/fragment parts, host is case-insensitive.
         • A valid URL's host must be exactly "open.spotify.com" and path must start with "/track/" followed by a 22-character base62 track ID.
         • Example: --url "https://open.spotify.com/track/5UsLjwBaTHBX4ektWIr4XX"

      3) --uri SPOTIFY_TRACK_URI
         • A single Spotify track URI.
         • Must be of the form "spotify:track:<track_id>" where <track_id> is the 22-character base62 ID.
         • Will be treated case-sensitively.
         • Example: --uri "spotify:track:5UsLjwBaTHBX4ektWIr4XX"

      4) --batch FILE
         • Each non-empty, non-comment line defines one song.
         • Comment lines start with a '#' (hash).
         • Blank lines as well as comment lines are ignored.
         • Lines may be:
              title=<song title>
              title=<song title>[TAB]artist=<artist1,artist2,...>
              url=<spotify track url>
              uri=<spotify track uri>
         • Mixture of song spec types in the same line (other than title/artist) might cause for the search to fail.

    Notes:
      • [TAB] means an actual tab character, not spaces.
      • Quoting is only required on the command line, and shouldn't be used in batch files.
      • <track_id> is the 22-character base62 ID found in Spotify track URLs and URIs.
      • Exactly one of the four input modes must be chosen.
    """)

    p = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawTextHelpFormatter,
        prog="song_specs",
    )
    g = p.add_mutually_exclusive_group(required=True)

    # -----------------------------------Mutually exclusive group-----------------------------------
    # Single-spec inputs
    g.add_argument(
        "--title",
        metavar="TITLE",
        help="Song title when specifying manually. --artist will be meaningful only if --title is given.",
        type=song_title,
    )
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

    # Batch file
    g.add_argument(
        "--batch",
        metavar="FILE",
        help="Path to a batch file (must be readable). Blank lines and comment lines starting with # (hash) are ignored.",
        type=readable_file,
    )
    # ----------------------------------------------------------------------------------------------

    p.add_argument(
        "--artist",
        metavar="ARTIST[,ARTIST,...]",
        help="One or more artists separated by commas. Only meaningful if --title is given.",
        type=artist_list,
        default=[],
    )

    return p


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()
    return args


def main():
    try:
        args = parse_args()
        print(args)
    except SystemExit:
        pass


if __name__ == "__main__":
    t = "It's Up (feat. Young Thug & 21 Savage)"
    print(clean_title_for_genius(t))
