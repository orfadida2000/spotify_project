from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from tqdm import tqdm

from sp2genius.constants.text import EM_DASHES
from sp2genius.genius.api.client import genius_url_for_title_artists
from sp2genius.lyrics.argparse import normalize_artist_list, normalize_song_title
from sp2genius.utils.path import (
    is_dir,
    is_file,
    is_readable_dir,
    is_readable_file,
    is_writable_dir,
)
from sp2genius.utils.typing import ReturnCode

from .typing import AUDIO_EXTS, SearchOutcome, SearchSummary


def load_log_file(
    log_file_path: Path,
) -> tuple[dict[str, tuple[SearchOutcome, str]], SearchSummary]:
    """
    Load existing log file into a dictionary mapping filenames to log entries.
    """
    summary: SearchSummary = SearchOutcome.empty_search_summary()
    log_data: dict[str, tuple[SearchOutcome, str]] = {}
    ret_code, p, err = is_file(log_file_path)
    if ret_code == ReturnCode.NOT_FOUND:
        pass
    elif ret_code != ReturnCode.SUCCESS or p is None:
        raise OSError(f"Failed to access log file: {err}")
    else:
        log_file_path = p
        ret_code, p, err = is_readable_file(log_file_path)
        if ret_code != ReturnCode.SUCCESS:
            raise OSError(f"Log file is not readable: {err}")
        try:
            with log_file_path.open("r", encoding="utf-8", errors="replace", newline=None) as f:
                outcome: SearchOutcome | None = None
                for line in f:
                    line = line.strip()
                    skip_prefix_lst = ["Total:", "#"] + [f"{o}:" for o in SearchOutcome]
                    if not line or any(line.startswith(prefix) for prefix in skip_prefix_lst):
                        continue
                    for o in SearchOutcome:
                        if o.separator in line:
                            outcome = o
                            break
                    if outcome is None:
                        continue

                    summary[outcome] += 1
                    filename, msg = line.rsplit(sep=outcome.separator, maxsplit=1)
                    filename = filename.strip()
                    msg = msg.strip()
                    if not filename or not msg:
                        continue
                    log_data[filename] = (outcome, msg)
        except OSError as e:
            raise OSError(
                f"An unexpected error occurred while reading the log file: {log_file_path}"
            ) from e
    return log_data, summary


def _split_artist_title_by_filename(filename: str) -> tuple[int, str, str] | tuple[int, str]:
    if not filename:
        return 1, "Filename is empty"
    for tok in EM_DASHES:
        sep = f" {tok} "
        res = filename.split(sep, 1)
        if len(res) == 1:
            continue
        artist, title = res
        if not artist.strip() or not title.strip():
            continue
        return 0, artist, title
    return 1, "Filename does not match '<artist> - <title>' pattern"


def process_dir_for_spotify(
    track_dir_path: Path,
    log_file_path: Path,
    trust_log: bool = False,
    exts: Iterable[str] = AUDIO_EXTS,
    verbose: bool = False,
    extra_artists_lst: list[str] | None = None,
) -> SearchSummary | None:
    """
    Scan a directory for audio files named '<primary artist> - <song title>.<ext>',
    query Genius via `genius_url_for_title_artists`, and write a TSV log.

    Returns: (total, found, not_found, skipped)
    """
    if extra_artists_lst is None:
        extra_artists_lst = []
    extra_artists_lst = [a.strip() for a in extra_artists_lst if a.strip()]
    exts_lc = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
    summary: SearchSummary = SearchOutcome.empty_search_summary()
    line_groups: dict[SearchOutcome, list[str]] = {o: [] for o in SearchOutcome}
    log_data: dict[str, tuple[SearchOutcome, str]] = {}
    if trust_log:
        log_data, log_summary = load_log_file(log_file_path)

    iter = track_dir_path.iterdir()
    files = sorted(iter)
    for f in tqdm(iterable=files, desc="Processing audio files", unit="file", total=len(files)):
        url = None
        msg = None
        outcome: SearchOutcome
        filename = f.stem
        if filename in log_data:
            outcome, msg = log_data[filename]
        else:
            ret_code, _, _ = is_file(f)
            if ret_code != ReturnCode.SUCCESS:
                outcome = SearchOutcome.SKIPPED
                msg = "Not a file"
            elif f.suffix.lower() not in exts_lc:
                outcome = SearchOutcome.SKIPPED
                msg = "Not an audio file"
            else:
                ext_code, *split = _split_artist_title_by_filename(filename)
                if ext_code != 0:
                    outcome = SearchOutcome.SKIPPED
                    msg = split[0]
                else:
                    artist, title = split
                    try:
                        norm_title = normalize_song_title(title)
                        norm_artist_lst = normalize_artist_list(artist)
                        if not norm_title:
                            outcome = SearchOutcome.SKIPPED
                            msg = "Track title isn't a valid track title"
                        elif not norm_artist_lst:
                            outcome = SearchOutcome.SKIPPED
                            msg = "Artist name isn't a valid artist name"
                        else:
                            norm_artist_set = {a.lower() for a in norm_artist_lst}
                            for a in extra_artists_lst:
                                if a.lower() not in norm_artist_set:
                                    norm_artist_lst.append(a)
                            url = genius_url_for_title_artists(
                                title=norm_title,
                                artist_lst=norm_artist_lst,
                            )
                            if url:
                                outcome = SearchOutcome.FOUND
                                msg = url
                            else:
                                outcome = SearchOutcome.NOT_FOUND
                                msg = "404 not found"
                    except Exception:
                        outcome = SearchOutcome.NOT_FOUND
                        msg = "An exception occurred during Genius URL retrieval"

        line_groups[outcome].append(f"{filename}    {outcome.separator} {msg}")
        summary[outcome] += 1

    total = SearchOutcome.get_total(summary)

    # write log
    try:
        with log_file_path.open("w", encoding="utf-8", newline="\n") as out:
            for o in sorted(SearchOutcome, key=lambda o: str(o)):
                out.write(f"\n# {o}:\n")
                lines = line_groups[o]
                for line in lines:
                    out.write(line + "\n")
            out.write("\n\n")
            for o in sorted(SearchOutcome, key=lambda o: str(o)):
                count = summary[o]
                out.write(f"{o}: {count}\n")
            out.write(f"Total: {total}\n")
    except Exception:
        print(f"Error: an exception occurred during log writing: {log_file_path}")
        return None

    return summary


def readable_dir_path(path_str: str) -> Path:
    """
    Argparse type function: Directory path
    Ensure the path exists and is a directory.
    Return the path as a Path object if valid.
    Otherwise raise argparse.ArgumentTypeError.
    """
    return_code, p, err = is_readable_dir(path_str)
    if return_code != ReturnCode.SUCCESS or p is None:
        raise argparse.ArgumentTypeError(f"Invalid readable directory path: {err}")
    return p


def writable_dir_path(path_str: str) -> Path:
    """
    Argparse type function: Writable directory path
    Ensure the path exists and is a writable directory.
    Return the path as a Path object if valid.
    Otherwise raise argparse.ArgumentTypeError.
    """
    return_code, p, err = is_writable_dir(path_str)
    if return_code != ReturnCode.SUCCESS or p is None:
        raise argparse.ArgumentTypeError(f"Invalid writable directory path: {err}")
    return p


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tag audio files in a directory with Genius URLs based on their filenames."
    )
    parser.add_argument(
        "--path",
        type=readable_dir_path,
        required=True,
        help="Path to the directory containing audio files.",
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default=None,
        help="Path to the directory to save the log file. Defaults to the input directory. The log file is named 'genius_search.log'.",
    )
    parser.add_argument(
        "--trust-log",
        action="store_true",
        help="Trust existing log file and skip re-processing files already logged.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    return parser


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()
    if args.log_path is None:
        args.log_path = args.path
    return_code, p, err = is_dir(args.log_path)
    if return_code != ReturnCode.SUCCESS or p is None:
        parser.error(f"Invalid log directory path: {err}")
    args.log_path = p
    args.log_file = args.log_path / "genius_search.log"
    return args


def main():
    args = parse_args()

    summary = process_dir_for_spotify(
        track_dir_path=args.path,
        log_file_path=args.log_file,
        trust_log=args.trust_log,
        exts=AUDIO_EXTS,
        verbose=args.verbose,
        extra_artists_lst=[],  # Example extra artists
    )
    if summary is None:
        print("Processing failed due to an error.")
    else:
        print("Processing completed successfully.")
        print(f"Saved log file to: {args.log_file}")
        if args.verbose:
            total = SearchOutcome.get_total(summary)
            for o in sorted(SearchOutcome, key=lambda o: str(o)):
                count = summary[o]
                print(f"{o}: {count}")
            print(f"Total: {total}")


if __name__ == "__main__":
    main()
