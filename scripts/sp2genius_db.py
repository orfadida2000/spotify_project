from pathlib import Path

ABS_FILE_PATH = Path(__file__).resolve()
ABS_ROOT_DIR_PATH = ABS_FILE_PATH.parent.parent
DB_PATH = ABS_ROOT_DIR_PATH / "lyrics_db"
DELIM = "\t"


def load_db():
    try:
        if not DB_PATH.exists():
            return (None, 1)
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

        return (data, 0)
    except Exception:
        return (None, 2)


def get_value_from_db(key: str) -> str:
    tup = load_db()
    if tup[1] != 0:
        return ""
    d = tup[0]
    return d.get(key, "")


def set_value_in_db(key: str, value: str):
    d, exit_code = load_db()
    if exit_code == 2:  # read error → stop
        return

    try:
        if exit_code == 1:
            # file missing → create new one
            with DB_PATH.open(mode="w", encoding="utf-8", errors="strict", newline="\n") as f:
                f.write(f"{key}{DELIM}{value}\n")
            return
    except Exception:
        return

    try:
        d = d if isinstance(d, dict) else {}
        d[key] = value
        # rewrite entire file
        with DB_PATH.open(mode="w", encoding="utf-8", errors="strict", newline="\n") as f:
            for k, v in d.items():
                f.write(f"{k}{DELIM}{v}\n")
    except Exception:
        return
