from collections.abc import Iterable
from enum import Enum

import colorama
from termcolor import colored

__all__ = [
    "init_console",
    "colorize_text",
    "TermForegroundColor",
    "TermBackgroundColor",
    "TermTextAttribute",
]

_initialized = False


class TermForegroundColor(Enum):
    # Black and white foreground colors
    BLACK = "black"
    WHITE = "white"

    # Grey foreground colors
    LIGHT_GREY = "light_grey"
    DARK_GREY = "dark_grey"

    # Standard foreground colors
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    MAGENTA = "magenta"
    CYAN = "cyan"

    # Light foreground colors
    LIGHT_RED = "light_red"
    LIGHT_GREEN = "light_green"
    LIGHT_YELLOW = "light_yellow"
    LIGHT_BLUE = "light_blue"
    LIGHT_MAGENTA = "light_magenta"
    LIGHT_CYAN = "light_cyan"


class TermBackgroundColor(Enum):
    # Black and white background colors
    BLACK = "on_black"
    WHITE = "on_white"

    # Grey background colors
    LIGHT_GREY = "on_light_grey"
    DARK_GREY = "on_dark_grey"

    # Standard background colors
    RED = "on_red"
    GREEN = "on_green"
    YELLOW = "on_yellow"
    BLUE = "on_blue"
    MAGENTA = "on_magenta"
    CYAN = "on_cyan"

    # Light background colors
    LIGHT_RED = "on_light_red"
    LIGHT_GREEN = "on_light_green"
    LIGHT_YELLOW = "on_light_yellow"
    LIGHT_BLUE = "on_light_blue"
    LIGHT_MAGENTA = "on_light_magenta"
    LIGHT_CYAN = "on_light_cyan"


class TermTextAttribute(Enum):
    BOLD = "bold"
    DARK = "dark"
    ITALIC = "italic"
    UNDERLINE = "underline"
    BLINK = "blink"
    REVERSE = "reverse"
    CONCEALED = "concealed"
    STRIKE = "strike"


def init_console(*, force: bool = False) -> None:
    """
    Initialize console color support.

    Args:
        force (bool): If True, re-run initialization even if already initialized. Default to False.

    Notes:
        - This function uses colorama to initialize console color support.
        - It must be called explicitly (typically from the program entry point).
        - It must not be invoked at import time.
        - On Windows, Colorama wraps stdout/stderr to translate ANSI escapes into Win32 calls.
        - On non-Windows platforms, it is effectively a no-op / passthrough.
        - This function uses Colorama's defaults (strip=None, convert=None) so it can decide
          per-stream (sys.stdout/sys.stderr) based on whether the stream is attached to a TTY.
    """
    global _initialized

    if _initialized and not force:
        return

    colorama.init()
    _initialized = True


def colorize_text(
    text: str,
    fg_color: TermForegroundColor | None = None,
    bg_color: TermBackgroundColor | None = None,
    text_attrs: Iterable[TermTextAttribute] | None = None,
) -> str:
    """
    Colorize text using termcolor, with enums as the source of truth.

    Args:
        text (str): The text to colorize.
        fg_color (TermForegroundColor | None): The foreground color. Default to None (i.e., no color).
        bg_color (TermBackgroundColor | None): The background color. Default to None (i.e., no background color).
        text_attrs (Iterable[TermTextAttribute] | None): Text attributes. Default to None (i.e., no attributes).

    Returns:
        str: The colorized text (with ANSI escape sequences).
    """
    if fg_color is None:
        color = None
    elif isinstance(fg_color, TermForegroundColor):
        color = fg_color.value
    else:
        color = None  # when invalid, fall back to no color

    if bg_color is None:
        on_color = None
    elif isinstance(bg_color, TermBackgroundColor):
        on_color = bg_color.value
    else:
        on_color = None  # when invalid, fall back to no background color

    if text_attrs is None:
        attrs = None
    elif isinstance(text_attrs, Iterable):
        attrs = {attr.value for attr in text_attrs if isinstance(attr, TermTextAttribute)}
    else:
        attrs = None  # when invalid, fall back to no text attributes

    return colored(
        text,
        color=color,
        on_color=on_color,
        attrs=attrs,
    )
