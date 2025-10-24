from pathlib import Path
from typing import Final

DEBUG_MODE: Final[bool] = False

ABS_TOP_PKG_PATH: Final[Path] = Path(__file__).resolve().parent
