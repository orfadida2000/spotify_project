from __future__ import annotations

import base64
import json
import time

import requests

from .constants import _TOKEN_CACHE_PATH, _TOKEN_SAFETY_MARGIN, SP_AUTH


def _load_cached_token() -> dict | None:
    """Load cached token data from disk, if available and readable."""
    if not _TOKEN_CACHE_PATH.is_file():
        return None

    try:
        raw = _TOKEN_CACHE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    # Basic sanity check on required fields
    if not all(k in data for k in ("auth", "access_token", "expires_at")):
        return None

    try:
        data["expires_at"] = float(data["expires_at"])
    except (TypeError, ValueError):
        return None

    return data


def _store_cached_token(auth: str, access_token: str, expires_at: float) -> None:
    """Persist token data to disk (best effort, failures are ignored)."""
    cache_data = {
        "auth": auth,
        "access_token": access_token,
        "expires_at": expires_at,
    }

    tmp_path = _TOKEN_CACHE_PATH.with_suffix(_TOKEN_CACHE_PATH.suffix + ".tmp")
    try:
        tmp_path.write_text(json.dumps(cache_data), encoding="utf-8")
        tmp_path.replace(_TOKEN_CACHE_PATH)
    except OSError:
        # Cache write is best-effort; ignore failures.
        pass


def _fetch_new_token(auth: str) -> str:
    """Actually call Spotify and get a fresh token, then cache it."""
    resp = requests.post(
        SP_AUTH,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}"},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()

    access_token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 3600))  # seconds; default 1h if missing
    now = time.time()
    # Store the real expiry minus a small safety margin
    expires_at = now + max(0, expires_in - _TOKEN_SAFETY_MARGIN)

    _store_cached_token(auth=auth, access_token=access_token, expires_at=expires_at)
    return access_token


def _get_token(client_id: str, client_secret: str) -> str:
    """
    Get a Spotify access token.

    Reuses a cached token if:
    - it exists
    - it hasn't expired yet (with safety margin)
    - it was generated using the same client_id/client_secret pair
    """
    # This is your original "auth" value, now also used as a cache key
    auth_bytes = f"{client_id}:{client_secret}".encode()
    auth = base64.b64encode(auth_bytes).decode("ascii")

    now = time.time()
    cache = _load_cached_token()

    if cache is not None and cache["auth"] == auth and cache["expires_at"] > now:
        return str(cache["access_token"])

    # No cache, wrong client, or expired token -> fetch a new one
    return _fetch_new_token(auth)
