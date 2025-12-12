from pathlib import Path
from typing import Final

from sp2genius.constants.path import ROOT_DIR_PATH
from sp2genius.utils.path import get_absolute_path

DB_PATH: Final[Path] = get_absolute_path(ROOT_DIR_PATH / "db" / "music_metadata.db")
