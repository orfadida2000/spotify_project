from datetime import datetime
from typing import Any

from sp2genius.utils.normalization import filter_by_spec, validate_normalize_fields

from .constants import (
    ALBUM_FIELD_REQUIREMENTS,
    ALBUM_SPECS,
    ARTIST_FIELD_REQUIREMENTS,
    ARTIST_SPECS,
    MEDIA_FIELD_REQUIREMENTS,
    MEDIA_SPECS,
    SONG_FIELD_REQUIREMENTS,
    SONG_SPECS,
    YOUTUBE_VIDEO_URL_RE,
)


def _normalize_date(date_str: str, norm_date_format: str = "%Y-%m-%d") -> str:
    d = datetime.strptime(date_str, "%B %d, %Y").date()
    return d.strftime(norm_date_format)


def _normalize_image_urls(image_url_lst: list[str]) -> str | None:
    for url in image_url_lst:
        # Extra safety, even though validate_normalize_fields should have already stripped it
        if url.strip():
            return url.strip()
    return None


def _normalize_song_media(media: dict[str, str], is_filtered: bool = False) -> dict[str, str]:
    filtered_media = media if is_filtered else filter_by_spec(media, MEDIA_SPECS)
    norm_media = validate_normalize_fields(
        filtered_data=filtered_media,
        field_requirements=MEDIA_FIELD_REQUIREMENTS,
        entity_name="Media",
    )
    return norm_media


def _normalize_song_media_lst(
    media_lst: list[dict[str, str]],
    allowed_providers: set[str],
    is_filtered: bool = False,
) -> list[dict[str, str]]:
    if not isinstance(media_lst, list):
        raise TypeError("Media list must be a list of dictionaries.")
    if not isinstance(allowed_providers, set):
        raise TypeError("Allowed providers must be a set of strings.")
    normalized_lst = []
    allowed_providers = {p.strip().lower() for p in allowed_providers}
    for media in media_lst:
        norm_media = _normalize_song_media(media, is_filtered=is_filtered)
        provider = norm_media["provider"].lower()
        if provider in allowed_providers:
            normalized_lst.append(norm_media)
    return normalized_lst


def _normalize_song_media_youtube(
    media_lst: list[dict[str, str]], is_filtered: bool = False
) -> str | None:
    norm_lst = _normalize_song_media_lst(media_lst, {"youtube"}, is_filtered=is_filtered)
    if not norm_lst:
        return None
    youtube_url = norm_lst[0]["url"]
    match = YOUTUBE_VIDEO_URL_RE.fullmatch(youtube_url)
    if not match:
        return None
    return match.group(1)


def normalize_artist(artist_data: dict[str, Any], is_filtered: bool = False) -> dict[str, Any]:
    filtered_artist_data = artist_data if is_filtered else filter_by_spec(artist_data, ARTIST_SPECS)
    norm_artist = validate_normalize_fields(
        filtered_data=filtered_artist_data,
        field_requirements=ARTIST_FIELD_REQUIREMENTS,
        entity_name="Artist",
    )
    final_img_url = _normalize_image_urls(
        [
            norm_artist.pop("image_url", ""),
            norm_artist.pop("header_image_url", ""),
        ]
    )
    if final_img_url:
        norm_artist["image_url"] = final_img_url
    return norm_artist


def normalize_album(album_data: dict[str, Any], is_filtered: bool = False) -> dict[str, Any]:
    filtered_album_data = album_data if is_filtered else filter_by_spec(album_data, ALBUM_SPECS)
    norm_album = validate_normalize_fields(
        filtered_data=filtered_album_data,
        field_requirements=ALBUM_FIELD_REQUIREMENTS,
        entity_name="Album",
    )
    final_img_url = _normalize_image_urls([norm_album.pop("cover_art_url", "")])
    if final_img_url:
        norm_album["image_url"] = final_img_url

    norm_album["release_date"] = _normalize_date(norm_album.pop("release_date_for_display"))
    norm_album["primary_artist"] = normalize_artist(norm_album.pop("artist"), is_filtered=True)
    norm_album["title"] = norm_album.pop("name")
    return norm_album


def normalize_song(song_data: dict[str, Any], is_filtered: bool = False) -> dict[str, Any]:
    filtered_song_data = song_data if is_filtered else filter_by_spec(song_data, SONG_SPECS)
    norm_song = validate_normalize_fields(
        filtered_data=filtered_song_data,
        field_requirements=SONG_FIELD_REQUIREMENTS,
        entity_name="Song",
    )
    final_img_url = _normalize_image_urls(
        image_url_lst=[
            norm_song.pop("song_art_image_url", ""),
            norm_song.pop("header_image_url", ""),
            norm_song.pop("song_art_image_thumbnail_url", ""),
            norm_song.pop("header_image_thumbnail_url", ""),
        ]
    )
    if final_img_url:
        norm_song["image_url"] = final_img_url

    norm_song["release_date"] = _normalize_date(norm_song.pop("release_date_for_display"))
    norm_song["primary_artist"] = normalize_artist(norm_song["primary_artist"], is_filtered=True)

    all_artists_ids = {norm_song["primary_artist"]["id"]}
    all_artists = [norm_song["primary_artist"]]

    for artist in norm_song.pop("primary_artists", []):
        norm_artist = normalize_artist(artist, is_filtered=True)
        if norm_artist["id"] not in all_artists_ids:
            all_artists.append(norm_artist)
            all_artists_ids.add(norm_artist["id"])

    for artist in norm_song.pop("featured_artists", []):
        norm_artist = normalize_artist(artist, is_filtered=True)
        if norm_artist["id"] not in all_artists_ids:
            all_artists.append(norm_artist)
            all_artists_ids.add(norm_artist["id"])

    norm_song["featured_artists"] = all_artists[1:] if len(all_artists) > 1 else []

    youtube_video_id = _normalize_song_media_youtube(norm_song.pop("media", []), is_filtered=True)
    if youtube_video_id:
        norm_song["youtube_video_id"] = youtube_video_id

    norm_song["album"] = normalize_album(norm_song["album"], is_filtered=True)
    album_prim_artist = norm_song["album"]["primary_artist"]
    if album_prim_artist["id"] not in all_artists_ids:
        raise ValueError("Data inconsistency: Album's primary artist isn't among song artists")

    return norm_song
