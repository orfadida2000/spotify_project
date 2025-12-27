from sp2genius.utils.normalization import filter_by_spec, validate_normalize_fields

from .constants import (
    ALBUM_FIELD_REQUIREMENTS,
    ALBUM_SPECS,
    ARTIST_FIELD_REQUIREMENTS,
    ARTIST_SPECS,
    IMAGE_FIELD_REQUIREMENTS,
    IMAGE_SPECS,
    SPOTIFY_ID_RE,
    SPOTIFY_RELEASE_DATE_PATTERNS,
    TRACK_FIELD_REQUIREMENTS,
    TRACK_SPECS,
)


def _validate_spotify_release_date(release_date: str) -> None:
    """Spotify release_date can be in format YYYY, YYYY-MM or YYYY-MM-DD"""
    if not any(pattern.fullmatch(release_date) for pattern in SPOTIFY_RELEASE_DATE_PATTERNS):
        raise ValueError(f"Invalid Spotify release_date format: {release_date}")


def _validate_spotify_id(spotify_id: str) -> None:
    """Validate Spotify ID format"""
    if not SPOTIFY_ID_RE.fullmatch(spotify_id):
        raise ValueError(f"Invalid Spotify ID format: {spotify_id}")


def _validate_spotify_album_type(album_type: str) -> None:
    """Validate Spotify album_type value"""
    if album_type not in {"album", "single", "compilation"}:
        raise ValueError(f"Invalid Spotify album_type: {album_type}")


def normalize_image_info(image_data: dict, is_filtered: bool = False) -> dict:
    filtered_image_data = image_data if is_filtered else filter_by_spec(image_data, IMAGE_SPECS)
    norm_image = validate_normalize_fields(
        filtered_data=filtered_image_data,
        field_requirements=IMAGE_FIELD_REQUIREMENTS,
        entity_name="Image",
    )
    return norm_image


def normalize_images_info(image_data_lst: list[dict], is_filtered: bool = False) -> list[dict]:
    assert isinstance(image_data_lst, list)
    norm_image_lst = []
    for image_data in image_data_lst:
        norm_img_info = normalize_image_info(image_data, is_filtered=is_filtered)
        norm_image_lst.append(norm_img_info)
    return norm_image_lst


def normalize_artist_info(artist_data: dict, is_filtered: bool = False) -> dict:
    filtered_artist_data = artist_data if is_filtered else filter_by_spec(artist_data, ARTIST_SPECS)
    norm_artist = validate_normalize_fields(
        filtered_data=filtered_artist_data,
        field_requirements=ARTIST_FIELD_REQUIREMENTS,
        entity_name="Artist",
    )
    _validate_spotify_id(norm_artist["id"])

    total_followers = norm_artist.pop("followers", {}).get("total", None)
    if isinstance(total_followers, ARTIST_SPECS["followers"]["total"]):
        norm_artist["total_followers"] = total_followers

    genres = norm_artist.pop("genres", [])
    if len(genres) > 0:
        norm_artist["genres"] = ", ".join(genres)

    images = norm_artist.pop("images", [])
    if len(images) > 0:
        norm_artist["images"] = normalize_images_info(images, is_filtered=True)

    return norm_artist


def normalize_artists_info(artist_data_lst: list[dict], is_filtered: bool = False) -> list[dict]:
    assert isinstance(artist_data_lst, list)
    norm_artist_lst = []
    for artist_data in artist_data_lst:
        norm_artist = normalize_artist_info(artist_data, is_filtered=is_filtered)
        norm_artist_lst.append(norm_artist)
    return norm_artist_lst


def normalize_album_info(album_data: dict, is_filtered: bool = False) -> dict:
    filtered_album_data = album_data if is_filtered else filter_by_spec(album_data, ALBUM_SPECS)
    norm_album = validate_normalize_fields(
        filtered_data=filtered_album_data,
        field_requirements=ALBUM_FIELD_REQUIREMENTS,
        entity_name="Album",
    )
    _validate_spotify_id(norm_album["id"])
    _validate_spotify_release_date(norm_album["release_date"])
    _validate_spotify_album_type(norm_album["album_type"])

    norm_album["title"] = norm_album.pop("name")
    norm_album["primary_artist"] = normalize_artist_info(
        artist_data=norm_album.pop("artists")[0],
        is_filtered=True,
    )

    images = norm_album.pop("images", [])
    if len(images) > 0:
        norm_album["images"] = normalize_images_info(images, is_filtered=True)

    return norm_album


def normalize_albums_info(album_data_lst: list[dict], is_filtered: bool = False) -> list[dict]:
    norm_album_lst = []
    for album_data in album_data_lst:
        norm_album = normalize_album_info(album_data, is_filtered=is_filtered)
        norm_album_lst.append(norm_album)
    return norm_album_lst


def normalize_track_info(track_data: dict, is_filtered: bool = False) -> dict:
    filtered_track_data = track_data if is_filtered else filter_by_spec(track_data, TRACK_SPECS)
    norm_track = validate_normalize_fields(
        filtered_data=filtered_track_data,
        field_requirements=TRACK_FIELD_REQUIREMENTS,
        entity_name="Track",
    )
    _validate_spotify_id(norm_track["id"])

    norm_track["title"] = norm_track.pop("name")

    all_artists = normalize_artists_info(norm_track.pop("artists"), is_filtered=True)
    all_artists_ids = {artist["id"] for artist in all_artists}
    norm_track["primary_artist"] = all_artists[0]
    norm_track["featured_artists"] = all_artists[1:] if len(all_artists) > 1 else []

    norm_track["album"] = normalize_album_info(norm_track["album"], is_filtered=True)
    album_prim_artist = norm_track["album"]["primary_artist"]
    if album_prim_artist["id"] not in all_artists_ids:
        raise ValueError("Data inconsistency: Album's primary artist isn't among track artists")

    return norm_track


def normalize_tracks_info(track_data_lst: list[dict], is_filtered: bool = False) -> list[dict]:
    norm_track_lst = []
    for track_data in track_data_lst:
        norm_track = normalize_track_info(track_data, is_filtered=is_filtered)
        norm_track_lst.append(norm_track)
    return norm_track_lst
