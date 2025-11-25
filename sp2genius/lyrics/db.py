from sp2genius.constants.paths import DB_PATH
from sp2genius.constants.text import DELIM
from sp2genius.spotify.api.client import resolve_title_artists_from_spotify_url
from sp2genius.utils.path import is_readable_file, is_writable_dir
from sp2genius.utils.typing import ReturnCode


def load_db() -> tuple[bool, dict[str, str]]:
    exit_code, p, err = is_readable_file(DB_PATH)
    if exit_code == ReturnCode.NOT_FOUND:
        return False, {}
    elif exit_code != ReturnCode.SUCCESS or p is None:
        raise OSError(f"Failed to access lyrics database file: {err}")

    try:
        data = {}
        with DB_PATH.open(mode="r", encoding="utf-8", errors="replace", newline=None) as f:
            for line in f:
                line = line.strip()
                if "\ufffd" in line and not line.startswith("#"):
                    print("error: invalid character (�) in a non-comment line\n")
                    print(f"line: {line}\n")
                    continue
                if "\ufffd" in line or not line or line.startswith("#"):
                    continue
                if DELIM not in line:
                    print("error: invalid line format (missing delimiter)\n")
                    print(f"line: {line}\n")
                    continue
                k, v = line.split(DELIM, 1)
                data[k] = v

        return True, data
    except OSError as e:
        raise OSError("Failed to read lyrics database file") from e


def get_value_from_db(key: str) -> str:
    _, db = load_db()
    return db.get(key, "")


def set_value_in_db(key: str, value: str):
    db_exists, db = load_db()
    if not db_exists:
        exit_code, p, err = is_writable_dir(DB_PATH.parent)
        if exit_code != ReturnCode.SUCCESS or p is None:
            raise OSError(f"lyrics database directory: {err}")

    db[key] = value
    try:
        with DB_PATH.open(mode="w", encoding="utf-8", errors="strict", newline="\n") as f:
            for k, v in db.items():
                f.write(f"{k}{DELIM}{v}\n")
    except OSError as e:
        raise OSError("Failed to write lyrics database file") from e


def add_properties_to_db(url: str):
    title, artist_lst = resolve_title_artists_from_spotify_url(url)
    if not title or not artist_lst:
        raise ValueError("Could not resolve title and artists from Spotify URL")
    set_value_in_db(f"{url}|title", title)
    set_value_in_db(f"{url}|artists", ",".join(artist_lst))
