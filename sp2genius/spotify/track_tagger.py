from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .constants.text import AUDIO_EXTS, EM_DASHES
from .sp2genius_argparse import normalize_artist_list, normalize_song_title
from .sp2genius_viewer import genius_url_for_title_artists


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


def process_dir_for_genius(
    dir_path: str | Path,
    log_path: str | Path | None = None,
    exts: Iterable[str] = AUDIO_EXTS,
) -> tuple[int, int, int] | None:
    """
    Scan a directory for audio files named '<primary artist> - <song title>.<ext>',
    query Genius via `genius_url_for_title_artists`, and write a TSV log.

    Returns: (total, found, not_found)
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(dir_path)

    if log_path is None:
        log_path = dir_path / "genius_search.log"
    else:
        log_path = Path(log_path)

    exts_lc = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}

    total = found = not_found = 0
    lines: list[str] = []
    try:
        iter = dir_path.iterdir()
    except Exception:
        print(f"Error: an exception occurred during directory reading: {dir_path}")
        return None
    for f in sorted(iter):
        url = None
        err_msg = None
        if not f.is_file():
            continue
        if f.suffix.lower() not in exts_lc:
            continue

        total += 1
        abs_path = f.resolve()
        ext_code, *split = _split_artist_title_by_filename(f.stem)
        if ext_code != 0:
            err_msg = split[0]
        else:
            artist, title = split
            try:
                norm_title = normalize_song_title(title)
                norm_artist_lst = normalize_artist_list(artist)
                if not norm_title:
                    err_msg = "Track title isn't a valid track title"
                elif not norm_artist_lst:
                    err_msg = "Artist name isn't a valid artist name"
                else:
                    url = genius_url_for_title_artists(norm_title, norm_artist_lst)
                    if not url:
                        url = None
                        err_msg = "404 not found"
            except Exception:
                err_msg = "an exception occurred during Genius URL retrieval"

        if url is not None:
            lines.append(f"{abs_path}\tSuccess: {url}")
            found += 1
        else:
            lines.append(f"{abs_path}\tError: {err_msg}")
            not_found += 1

    # write log
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        print(f"Error: cannot create log directory: {log_path.parent}")
        return None
    try:
        with log_path.open("w", encoding="utf-8", newline="\n") as out:
            for line in lines:
                out.write(line + "\n")
            out.write("\n\n")
            out.write(f"Total songs:\t{total}\n")
            out.write(f"Found URLs:\t{found}\n")
            out.write(f"No URL:\t{not_found}\n")
    except Exception:
        print(f"Error: an exception occurred during log writing: {log_path}")
        return None

    return total, found, not_found
