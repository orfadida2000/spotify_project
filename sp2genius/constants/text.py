from typing import Final

DELIM: Final[str] = "\t"
EM_DASHES: Final[tuple[str, ...]] = ("—", "–", "―", "-")
AUDIO_EXTS: Final[set[str]] = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus"}

__all__ = [
    "DELIM",
    "EM_DASHES",
    "AUDIO_EXTS",
]
