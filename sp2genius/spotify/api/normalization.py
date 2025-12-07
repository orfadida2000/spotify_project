def normalize_image_info(data: dict) -> dict:
    image_info = {
        "url": data["url"],
        "width": data["width"],
        "height": data["height"],
    }
    return image_info


def normalize_images_info(data: list[dict]) -> list[dict]:
    images_info = []
    for img in data:
        img_info = normalize_image_info(img)
        images_info.append(img_info)
    return images_info


def normalize_artist_info(data: dict) -> dict:
    artist_info = {
        "id": data["id"],
        "name": data["name"],
        "total_followers": data.get("followers", {}).get("total", None),
        "genres": data.get("genres", None),
        "popularity": data.get("popularity", None),
        "images": normalize_images_info(data["images"]) if "images" in data else None,
    }
    artist_info = {k: v for k, v in artist_info.items() if v is not None}
    return artist_info


def normalize_artists_info(data: list[dict]) -> list[dict]:
    artists_info = []
    for artist in data:
        artist_info = normalize_artist_info(artist)
        artists_info.append(artist_info)
    return artists_info


def normalize_album_info(data: dict) -> dict:
    album_info = {
        "id": data["id"],
        "title": data["name"],
        "primary_artist_id": data["artists"][0]["id"],
        "type": data["album_type"],
        "total_tracks": data["total_tracks"],
        "release_date": data["release_date"],
        "label": data.get("label", None),
        "popularity": data.get("popularity", None),
        "images": normalize_images_info(data["images"]) if "images" in data else None,
    }
    album_info = {k: v for k, v in album_info.items() if v is not None}
    return album_info


def normalize_albums_info(data: list[dict]) -> list[dict]:
    albums_info = []
    for album in data:
        album_info = normalize_album_info(album)
        albums_info.append(album_info)
    return albums_info


def normalize_track_info(data: dict) -> dict:
    track_info = {
        "id": data["id"],
        "title": data["name"],
        "primary_artist": normalize_artist_info(data["artists"][0]),
        "featured_artists": normalize_artists_info(data["artists"][1:])
        if len(data["artists"]) > 1
        else [],
        "album": normalize_album_info(data["album"]),
        "disc_number": data["disc_number"],
        "track_number": data["track_number"],
        "duration_ms": data["duration_ms"],
        "explicit": data["explicit"],
        "popularity": data["popularity"],
    }
    artist_ids = [track_info["primary_artist"]["id"]] + [
        artist["id"] for artist in track_info["featured_artists"]
    ]
    if track_info["album"]["primary_artist_id"] not in artist_ids:
        raise ValueError("Data inconsistency: Album primary artist isn't among track artists")
    return track_info


def normalize_tracks_info(data: list[dict]) -> list[dict]:
    tracks_info = []
    for track in data:
        track_info = normalize_track_info(track)
        tracks_info.append(track_info)
    return tracks_info
