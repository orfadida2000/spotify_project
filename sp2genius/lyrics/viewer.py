import os
from pathlib import Path

from dotenv import load_dotenv
from lyricsgenius import Genius

from sp2genius.genius.constants import GENIUS_ENV_PATH, GENIUS_TOKEN_ENV_VAR
from sp2genius.spotify.title_artist_scraper import resolve_title_artists_from_spotify_url

from .argparse import (
    normalize_artist_list,
    normalize_song_title,
    normalize_track_uri,
    normalize_track_url,
    parse_args,
    spotify_track_uri_to_url,
)
from .db import get_value_from_db, set_value_in_db

load_dotenv(dotenv_path=GENIUS_ENV_PATH)
GENIUS_API_TOKEN = os.getenv(key=GENIUS_TOKEN_ENV_VAR)


def genius_url_for_title_artists(
    title: str,
    artist_lst: list[str],
    verbose: bool = False,
) -> str | None:
    try:
        token = GENIUS_API_TOKEN
        if not token or not title:
            return None
        g = Genius(
            access_token=token,
            timeout=10,
            skip_non_songs=True,
            remove_section_headers=False,
            verbose=verbose,
        )
        if len(artist_lst) == 0:
            song = g.search_song(title=title, get_full_info=False)
            return getattr(song, "url", None) if song else None
        for artist in artist_lst:
            song = g.search_song(title=title, artist=artist, get_full_info=False)
            if song:
                return song.url
        return None
    except Exception:
        return None


def process_url_mode(spotify_url: str) -> str | None:
    try:
        genius_url = get_value_from_db(spotify_url)
        if genius_url:
            return genius_url
        title, artist_lst = resolve_title_artists_from_spotify_url(spotify_url)
        if not title or not artist_lst:
            return None
        title = normalize_song_title(title)
        if not title:
            return None
        genius_url = genius_url_for_title_artists(title, artist_lst)
        if genius_url:
            set_value_in_db(spotify_url, genius_url)
            return genius_url
        return None
    except Exception:
        return None


def process_uri_mode(spotify_uri: str) -> str | None:
    try:
        spotify_url = spotify_track_uri_to_url(spotify_uri)
        return process_url_mode(spotify_url)
    except ValueError:
        return None


def process_title_mode(title: str, artist_lst: list[str]) -> str | None:
    try:
        genius_url = genius_url_for_title_artists(title, artist_lst)
        if genius_url:
            return genius_url
        return None
    except Exception:
        return None


def process_line(line: str) -> str:
    line = line.strip()
    if "\ufffd" in line and not line.startswith("#"):
        return line + " - error: invalid character (�) in a non-comment line\n"
    if "\ufffd" in line or not line or line.startswith("#"):
        return line + "\n"
    genius_url = None
    if line.startswith("url="):
        spotify_url = line.split("=", 1)[1]
        spotify_url = normalize_track_url(spotify_url)
        if not spotify_url:
            return line + " - error: invalid Spotify URL\n"
        genius_url = process_url_mode(spotify_url)
    elif line.startswith("uri="):
        spotify_uri = line.split("=", 1)[1]
        spotify_uri = normalize_track_uri(spotify_uri)
        if not spotify_uri:
            return line + " - error: invalid Spotify URI\n"
        genius_url = process_uri_mode(spotify_uri)
    elif line.startswith("title="):
        parts = [part.strip() for part in line.split("\t", 1)]
        title = parts[0].split("=", 1)[1]
        title = normalize_song_title(title)
        if not title:
            return line + " - error: invalid (empty) title\n"
        artist_lst = []
        if len(parts) == 2 and parts[1]:
            if not parts[1].startswith("artist="):
                return line + " - error: invalid manual mode line format\n"
            artists = parts[1].split("=", 1)[1]
            artist_lst = normalize_artist_list(artists)
        genius_url = process_title_mode(title, artist_lst)
    else:
        return line + " - error: invalid line format\n"

    if genius_url:
        return line + f" - success: {genius_url}\n"
    return line + " - error: 404 not found\n"


def process_batch_mode(file_path: Path) -> Path | None:
    try:
        output_path = file_path.with_suffix(suffix=".out.txt")
        with (
            file_path.open(mode="r", encoding="utf-8", errors="replace", newline=None) as i_file,
            output_path.open(mode="w", encoding="utf-8", errors="strict", newline="\n") as o_file,
        ):
            for line in i_file:
                line = process_line(line)
                o_file.write(line)
    except OSError:
        return None
    return output_path


def test():
    spotify_url = input("Enter Spotify track URL: ")
    print(f"Pre normalization URL : {spotify_url}")
    post_spotify_url = normalize_track_url(spotify_url)
    if not post_spotify_url:
        print("error: invalid Spotify URL")
        return
    print(f"Post normalization URL: {post_spotify_url}")
    try:
        title, artist_lst = resolve_title_artists_from_spotify_url(post_spotify_url)
        if not title or not artist_lst:
            print("error: could not resolve title and artist from Spotify URL")
            return
        print(f"Artist list: {artist_lst}")
        print(f"Pre normalization title : {title}")
        post_title = normalize_song_title(title)
        if not post_title:
            print("error: invalid (empty) title after normalization")
            return
        print(f"Post normalization title: {post_title}")
        genius_url = genius_url_for_title_artists(post_title, artist_lst)
        if genius_url:
            print(f"Success: {genius_url}")
            ans = input("Is this correct? (y/n): ").strip().lower()
            if ans == "y":
                set_value_in_db(post_spotify_url, genius_url)
                print("Saved to database.")
            else:
                print("Not saved to database.")
            return

        print("Error: 404 not found")
        return
    except Exception:
        print("error: exception occurred")
        return


def test_while_yes():
    ans = "y"
    print("\nStarting testing mode (Spotify URL to Genius URL)\n")
    while ans == "y":
        print("\n------------------------------------------------------------")
        test()
        print("------------------------------------------------------------")
        ans = input("Do you want to test another Spotify URL? (y/n): ").strip().lower()
    print("\nExiting testing mode.\n")


def main():
    try:
        args = parse_args()
    except SystemExit:
        return  # argparse already printed error message

    if args.batch:
        output_path = process_batch_mode(args.batch)
        if output_path:
            abs_output_path = output_path.resolve()
            print(f"Success: output written to {abs_output_path}")
        else:
            print("Error: could not process batch file.")
        return

    if args.url:
        genius_url = process_url_mode(args.url)
    elif args.uri:
        genius_url = process_uri_mode(args.uri)
    else:  # args.title must be defined
        genius_url = process_title_mode(args.title, args.artist)

    if genius_url:
        print(f"Success: {genius_url}")
    else:
        print("Error: 404 not found")


if __name__ == "__main__":
    main()
