import errno
import tempfile
from pathlib import Path

from sp2genius.utils.typing import ReturnCode


def get_home_path() -> Path:
    return Path.home()


def get_absolute_path(path: str | Path) -> Path | None:
    assert isinstance(path, (str, Path)), "The argument path must be a string or a Path object"
    path = path.strip() if isinstance(path, str) else path
    if not path:
        return None
    p = Path(path).expanduser().resolve(strict=False)
    return p


def is_existing_path(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    try:
        p = get_absolute_path(path)
    except RuntimeError:
        return (
            ReturnCode.TILDE_RESOLVE_FAILED,
            None,
            f"{ReturnCode.TILDE_RESOLVE_FAILED}: {path}",
        )
    except OSError:
        return ReturnCode.GENERAL_ERROR, None, f"{ReturnCode.GENERAL_ERROR}: {path}"

    if p is None:
        return ReturnCode.EMPTY_PATH, p, f"{ReturnCode.EMPTY_PATH}"

    try:
        p.stat()
    except FileNotFoundError:
        return ReturnCode.NOT_FOUND, p, f"{ReturnCode.NOT_FOUND}: {p}"
    except PermissionError:
        return ReturnCode.PERMISSION_DENIED, p, f"{ReturnCode.PERMISSION_DENIED}: {p}"
    except NotADirectoryError:
        return ReturnCode.NON_DIR_COMPONENT, p, f"{ReturnCode.NON_DIR_COMPONENT}: {p}"
    except OSError as e:
        if e.errno == errno.ENAMETOOLONG:
            return ReturnCode.NAME_TOO_LONG, p, f"{ReturnCode.NAME_TOO_LONG}: {p}"
        elif e.errno == errno.ELOOP:
            return ReturnCode.SYMLINK_LOOP, p, f"{ReturnCode.SYMLINK_LOOP}: {p}"
        return (
            ReturnCode.GENERAL_ERROR,
            p,
            f"{ReturnCode.GENERAL_ERROR} while verifying the path existence: {p}",
        )

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_dir(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    exit_code, p, err = is_existing_path(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    if not p.is_dir():
        return ReturnCode.NOT_DIR, p, f"{ReturnCode.NOT_DIR}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_file(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    """
    Return (is_file, Path, error_message).
    Uses is_existing_path() to verify existence and then checks type.
    """
    exit_code, p, err = is_existing_path(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    if not p.is_file():
        return ReturnCode.NOT_FILE, p, f"{ReturnCode.NOT_FILE}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_readable_dir(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    exit_code, p, err = is_dir(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    try:
        next(p.iterdir(), None)
    except OSError:
        return ReturnCode.NOT_READABLE_DIR, p, f"{ReturnCode.NOT_READABLE_DIR}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_readable_file(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    """
    Return (is_readable, Path, error_message).
    Uses is_file() to confirm file type, then attempts to open for read.
    """
    exit_code, p, err = is_file(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    try:
        with p.open("rb"):
            pass
    except OSError:
        return ReturnCode.NOT_READABLE_FILE, p, f"{ReturnCode.NOT_READABLE_FILE}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_writable_dir(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    exit_code, p, err = is_dir(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    # Try creating and deleting a temp file to confirm write permission
    try:
        with tempfile.NamedTemporaryFile(dir=p):
            pass
    except OSError:
        return ReturnCode.NOT_WRITABLE_DIR, p, f"{ReturnCode.NOT_WRITABLE_DIR}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"


def is_writable_file(path: str | Path) -> tuple[ReturnCode, Path | None, str]:
    """
    Return (is_writable, Path, error_message).
    Uses is_file() to confirm file type, then attempts to open for write (no truncate).
    """
    exit_code, p, err = is_file(path)
    if exit_code != ReturnCode.SUCCESS or p is None:
        return exit_code, p, err

    try:
        with p.open("ab"):  # Open for appending to avoid truncation
            pass
    except OSError:
        return ReturnCode.NOT_WRITABLE_FILE, p, f"{ReturnCode.NOT_WRITABLE_FILE}: {p}"

    return ReturnCode.SUCCESS, p, f"{ReturnCode.SUCCESS}"
