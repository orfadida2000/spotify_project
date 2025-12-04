from lyricsgenius import Genius

from . import GENIUS_API_TOKEN
from .constants import TIMEOUT


def genius_url_for_title_artists(
    title: str,
    artist_lst: list[str],
    verbose: bool = False,
) -> str:
    try:
        token = GENIUS_API_TOKEN
        if not token or not title:
            raise ValueError("Missing Genius API token or empty title.")
        g = Genius(
            access_token=token,
            timeout=TIMEOUT,
            skip_non_songs=True,
            remove_section_headers=False,
            verbose=verbose,
        )
        if len(artist_lst) == 0:
            song = g.search_song(title=title, get_full_info=False)
            url = getattr(song, "url", None) if song else None
            if not url:
                raise ValueError("404 could not find song URL on Genius.")
            return url
        for artist in artist_lst:
            song = g.search_song(title=title, artist=artist, get_full_info=True)
            url = getattr(song, "url", None) if song else None
            if url:
                data = song.to_dict()  # type: ignore
                import json

                with open("basic_genius_song_data.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return url
        raise ValueError("404 could not find song URL on Genius.")
    except Exception as e:
        raise ValueError(f"Genius API error: {e}") from None
