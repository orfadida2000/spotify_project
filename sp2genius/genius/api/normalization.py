from datetime import datetime
from typing import Any

from .constants import (
    ALBUM_SPECS,
    ARTIST_SPECS,
    MEDIA_SPECS,
    REQUIRED_ALBUM_FIELDS,
    REQUIRED_ARTIST_FIELDS,
    REQUIRED_MEDIA_FIELDS,
    REQUIRED_SONG_FIELDS,
    SONG_SPECS,
    YOUTUBE_VIDEO_URL_RE,
)


def _validate_normalize_fields(
    data: dict[str, Any],
    field_specs: dict[str, Any],
    required_fields: set[str],
    entity_name: str,
) -> None:
    if not isinstance(data, dict):
        raise TypeError(f"{entity_name} data must be a dictionary.")
    for field, field_spec in field_specs.items():
        field_type = field_spec if isinstance(field_spec, type) else type(field_spec)
        if field not in data:
            if field in required_fields:
                raise ValueError(f"{entity_name} data must contain a '{field}' field.")
            else:
                continue
        if not isinstance(data[field], field_type):
            raise TypeError(
                f"'{field}' field in {entity_name} data must be of type {field_type.__name__}."
            )
        data[field] = data[field].strip() if isinstance(data[field], str) else data[field]
        if not data[field]:
            if field in required_fields:
                raise ValueError(f"'{field}' field in {entity_name} data must not be empty.")


def _normalize_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%B %d, %Y")
    return dt.date().isoformat()


def _normalize_image_urls(image_url_lst: list[str]) -> str:
    for url in image_url_lst:
        if url.strip():
            return url.strip()
    return ""


def _normalize_media(media: dict[str, str]) -> dict[str, str]:
    _validate_normalize_fields(
        data=media,
        field_specs=MEDIA_SPECS,
        required_fields=REQUIRED_MEDIA_FIELDS,
        entity_name="Media",
    )
    norm_media = {k: v.strip() for k, v in media.items() if v}
    return norm_media


def _normalize_media_lst(
    media_lst: list[dict[str, str]], allowed_providers: set[str]
) -> list[dict[str, str]]:
    if not isinstance(media_lst, list):
        raise TypeError("Media list must be a list of dictionaries.")
    if not isinstance(allowed_providers, set):
        raise TypeError("Allowed providers must be a set of strings.")
    normalized_lst = []
    allowed_providers = {p.strip().lower() for p in allowed_providers}
    for media in media_lst:
        norm_media = _normalize_media(media)
        provider = norm_media["provider"].lower()
        if provider in allowed_providers:
            normalized_lst.append(norm_media)
    return normalized_lst


def _normalize_media_youtube(
    media_lst: list[dict[str, str]],
) -> str | None:
    norm_lst = _normalize_media_lst(media_lst, {"youtube"})
    if not norm_lst:
        return None
    youtube_url = norm_lst[0]["url"]
    match = YOUTUBE_VIDEO_URL_RE.fullmatch(youtube_url)
    if not match:
        return None
    return match.group(1)


def normalize_artist(artist_data: dict[str, Any]) -> dict[str, Any]:
    _validate_normalize_fields(
        data=artist_data,
        field_specs=ARTIST_SPECS,
        required_fields=REQUIRED_ARTIST_FIELDS,
        entity_name="Artist",
    )
    final_img_url = _normalize_image_urls(
        [
            artist_data.pop("image_url", ""),
            artist_data.pop("header_image_url", ""),
        ]
    )
    artist_data["image_url"] = final_img_url
    norm_artist = {k: v for k, v in artist_data.items() if v}
    return norm_artist


def normalize_album(album_data: dict[str, Any]) -> dict[str, Any]:
    _validate_normalize_fields(
        data=album_data,
        field_specs=ALBUM_SPECS,
        required_fields=REQUIRED_ALBUM_FIELDS,
        entity_name="Album",
    )
    final_img_url = _normalize_image_urls([album_data.pop("cover_art_url", "")])
    album_data["image_url"] = final_img_url
    album_data["release_date"] = _normalize_date(album_data.pop("release_date_for_display"))
    album_data["artist"] = normalize_artist(album_data["artist"])
    album_data["title"] = album_data.pop("name")
    norm_album = {k: v for k, v in album_data.items() if v}
    return norm_album


def normalize_song(song_data: dict[str, Any]) -> dict[str, Any]:
    _validate_normalize_fields(
        data=song_data,
        field_specs=SONG_SPECS,
        required_fields=REQUIRED_SONG_FIELDS,
        entity_name="Song",
    )
    final_img_url = _normalize_image_urls(
        image_url_lst=[
            song_data.pop("song_art_image_url", ""),
            song_data.pop("header_image_url", ""),
            song_data.pop("song_art_image_thumbnail_url", ""),
            song_data.pop("header_image_thumbnail_url", ""),
        ]
    )
    song_data["image_url"] = final_img_url
    song_data["release_date"] = _normalize_date(song_data.pop("release_date_for_display"))
    song_data["primary_artist"] = normalize_artist(song_data["primary_artist"])

    all_artists_ids = {song_data["primary_artist"]["id"]}
    all_artists = [song_data["primary_artist"]]

    for artist in song_data.pop("primary_artists", []):
        norm_artist = normalize_artist(artist)
        if norm_artist["id"] not in all_artists_ids:
            all_artists.append(norm_artist)
            all_artists_ids.add(norm_artist["id"])

    for artist in song_data.pop("featured_artists", []):
        norm_artist = normalize_artist(artist)
        if norm_artist["id"] not in all_artists_ids:
            all_artists.append(norm_artist)
            all_artists_ids.add(norm_artist["id"])

    song_data["featured_artists"] = all_artists[1:] if len(all_artists) > 1 else []

    youtube_video_id = _normalize_media_youtube(song_data.pop("media", []))
    if youtube_video_id:
        song_data["youtube_video_id"] = youtube_video_id

    song_data["album"] = normalize_album(song_data["album"])

    norm_song = {k: v for k, v in song_data.items() if v}
    return norm_song
