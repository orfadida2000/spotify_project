from enum import IntEnum
from typing import Final, TypeAlias

SearchSummary: TypeAlias = list[int]


class SearchOutcome(IntEnum):
    separator: str

    FOUND = 0, "Success:"
    NOT_FOUND = 1, "Error:"
    SKIPPED = 2, "Skipped:"

    def __new__(cls, value: int, separator: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.separator = separator
        return obj

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()

    @classmethod
    def empty_search_summary(cls) -> SearchSummary:
        return [0 for _ in cls]

    @staticmethod
    def get_total(summary: SearchSummary) -> int:
        return sum(summary)


AUDIO_EXTS: Final[set[str]] = {
    "mp3",
    "m4a",
    "wav",
    "ogg",
    "aac",
    "opus",
    "flac",
    "alac",
    "wma",
    "aiff",
}
