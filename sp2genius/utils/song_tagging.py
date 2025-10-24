#!/usr/bin/env python3
# Requirements: pip install mutagen

from datetime import datetime
from mimetypes import guess_type
from pathlib import Path

from mutagen.id3 import (
    APIC,  # type: ignore
    ID3,
    TALB,  # type: ignore
    TCOM,  # type: ignore
    TCON,  # type: ignore
    TDRC,  # type: ignore
    TIT2,  # type: ignore
    TPE1,  # type: ignore
    TPE2,  # type: ignore
    TPOS,  # type: ignore
    TRCK,  # type: ignore
    TYER,  # type: ignore
    ID3NoHeaderError,  # type: ignore
)

# ==== USER CONSTANTS ====
DIR = Path(r"songs")
IMAGE_PATH = Path(r"eminem_album_cover.jpg")
# ========================

ALBUM = "Unreleased Collection (Deluxe Edition)"
ALBUM_ARTIST = "Eminem"
ARTIST = "Eminem"
COMPOSER = "Eminem"
GENRE = "Hip-Hop"
DATE_ISO = "2000-12-20"
YEAR = "2000"
TRACKS_PER_DISC = 26


def detect_mime(p: Path) -> str:
    mime, _ = guess_type(p.as_posix())
    if mime in {"image/jpeg", "image/png", "image/gif"}:
        return mime
    return "image/jpeg"


def ensure_id3(path: Path) -> ID3:
    try:
        return ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
        tags.save(path)
        return ID3(path)


def sorted_mp3s(root: Path) -> list[Path]:
    return sorted([p for p in root.glob("*.mp3") if p.is_file()], key=lambda x: x.name.lower())


def parse_title_and_date(raw_title: str) -> tuple[str, str, str]:
    """
    Split by '#'.
    If parts >= 2 and parts[1] matches YYYY-MM-DD (and is a real calendar date),
    use parts[0] as title and parts[1] as date. Else keep title and default date.
    Returns: (title, yyyy_mm_dd, year)
    """
    # print(raw_title)
    parts = [s.strip() for s in raw_title.split("#")]
    if len(parts) >= 2:
        candidate_date = parts[1]
        if len(candidate_date) == 10:
            try:
                dt = datetime.strptime(candidate_date, "%Y-%m-%d").date()
                return parts[0] or raw_title, candidate_date, str(dt.year)
            except ValueError:
                pass
    return raw_title, DATE_ISO, YEAR


def main() -> None:
    mp3_files = sorted_mp3s(DIR)
    if not mp3_files:
        return

    cover_bytes = IMAGE_PATH.read_bytes()
    cover_mime = detect_mime(IMAGE_PATH)

    for idx, mp3 in enumerate(mp3_files, start=1):
        tags = ensure_id3(mp3)

        # Base title from existing tag or filename
        # Base title from existing tag (if any)
        frame = tags.get("TIT2")
        tag_title = frame.text[0] if frame else None

        # Prefer filename for parsing if it contains '#'
        name_for_parse = mp3.stem if "#" in mp3.stem else (tag_title or mp3.stem)

        # Parse title + date
        new_title, date_iso, year = parse_title_and_date(name_for_parse)

        # If we parsed from filename only to get the date, but you already have a clean tag title,
        # keep the tag title (avoid replacing it with filename-derived text)
        if tag_title and "#" not in tag_title:
            new_title = tag_title
        title = new_title

        # Compute track and disc
        track_num = idx
        disc_num = (idx - 1) // TRACKS_PER_DISC + 1

        # Set core text frames (UTF-8)
        tags["TIT2"] = TIT2(encoding=3, text=title)
        tags["TPE1"] = TPE1(encoding=3, text=ARTIST)
        tags["TALB"] = TALB(encoding=3, text=ALBUM)
        tags["TPE2"] = TPE2(encoding=3, text=ALBUM_ARTIST)
        tags["TCOM"] = TCOM(encoding=3, text=COMPOSER)
        tags["TCON"] = TCON(encoding=3, text=GENRE)
        tags["TRCK"] = TRCK(encoding=3, text=str(track_num))
        tags["TPOS"] = TPOS(encoding=3, text=str(disc_num))

        # Dates: write both TDRC (v2.4) and TYER (v2.3) for compatibility
        tags["TDRC"] = TDRC(encoding=3, text=date_iso)
        tags["TYER"] = TYER(encoding=3, text=year)

        # Replace existing cover(s) with the provided one
        # Remove prior APIC frames to avoid duplicates
        for k in list(tags.keys()):
            if k.startswith("APIC"):
                del tags[k]
        tags.add(APIC(encoding=3, mime=cover_mime, type=3, desc="Cover", data=cover_bytes))

        # Save as ID3v2.3 for maximum player compatibility
        tags.save(mp3, v2_version=3)
        # Save as ID3v2.3 for compatibility

        # === Rename file according to new title ===
        safe_title = new_title.replace("/", "-").replace("\\", "-").strip()
        new_path = mp3.with_name(f"{safe_title}.mp3")
        if new_path != mp3:
            mp3.rename(new_path)


if __name__ == "__main__":
    main()
