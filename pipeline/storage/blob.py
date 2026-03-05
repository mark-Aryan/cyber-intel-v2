"""
pipeline/storage/blob.py
=========================
All Vercel Blob interactions for the pipeline (running in GitHub Actions).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from pipeline.utils.helpers import get_logger, safe_json_default

log = get_logger(__name__)

BLOB_API       = "https://blob.vercel-storage.com"
DATA_JSON_PATH = "data.json"
TIMEOUT        = 30.0


CONTENT_TYPES = {
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


# ── data.json ──────────────────────────────────────────────────────────────────

async def load_data_json() -> dict[str, Any]:
    """
    Download and parse data.json from Vercel Blob.
    Returns an empty scaffold if the file doesn't exist (first run).
    """
    token = _get_token()
    url   = await _find_blob_url(DATA_JSON_PATH, token)

    if url is None:
        log.info("[blob] data.json not found — first run, starting fresh")
        return _scaffold()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.error("[blob] Could not load data.json: %s — starting fresh", exc)
        return _scaffold()


async def save_data_json(data: dict[str, Any]) -> str:
    """Serialise and upload data.json to Vercel Blob. Returns public CDN URL."""
    payload = json.dumps(data, default=safe_json_default, indent=2, ensure_ascii=False)
    url = await _put_blob(DATA_JSON_PATH, payload.encode("utf-8"), "application/json")
    log.info("[blob] data.json saved → %s", url)
    return url


# ── Images ─────────────────────────────────────────────────────────────────────

async def upload_image_to_blob(pathname: str, image_bytes: bytes) -> str:
    """Upload a generated image and return its public CDN URL."""
    ext          = "." + pathname.rsplit(".", 1)[-1].lower()
    content_type = CONTENT_TYPES.get(ext, "image/png")
    return await _put_blob(pathname, image_bytes, content_type)


# ── Internal ───────────────────────────────────────────────────────────────────

async def _put_blob(pathname: str, data: bytes, content_type: str) -> str:
    """PUT a blob via the Vercel Blob REST API."""
    token   = _get_token()
    headers = {
        "Authorization":       f"Bearer {token}",
        "x-content-type":      content_type,
        "x-add-random-suffix": "0",
        "Cache-Control":       "public, max-age=60",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.put(f"{BLOB_API}/{pathname}", content=data, headers=headers)
        r.raise_for_status()
        return r.json().get("url", f"{BLOB_API}/{pathname}")


async def _find_blob_url(pathname: str, token: str) -> str | None:
    """Use the Blob list API to find the CDN URL of a stored file."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"{BLOB_API}?prefix={pathname}&limit=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        blobs = r.json().get("blobs", [])
        return blobs[0]["url"] if blobs else None


def _get_token() -> str:
    """
    Read and sanitise the Vercel Blob token.

    The .strip() call is the critical fix: when pasting secrets into the
    GitHub Secrets UI, invisible trailing newlines or spaces are common.
    httpx rejects HTTP headers that contain whitespace/control characters,
    producing the cryptic 'Illegal header value b\"***\"' error.
    """
    raw   = os.getenv("BLOB_READ_WRITE_TOKEN", "")
    token = raw.strip()                          # ← removes \n \r \t spaces

    if not token:
        raise EnvironmentError(
            "BLOB_READ_WRITE_TOKEN is not set.\n"
            "  Add it in: GitHub repo → Settings → Secrets and variables → Actions\n"
            "  Get the value from: Vercel Dashboard → Storage → Blob → .env.local"
        )

    # Sanity-check the format so bad pastes fail early with a clear message
    if not re.match(r"^vercel_blob_rw_[A-Za-z0-9]+$", token):
        log.warning(
            "[blob] BLOB_READ_WRITE_TOKEN has unexpected format "
            "(first 25 chars: %r). Expected 'vercel_blob_rw_<alphanumeric>'. "
            "Re-copy the token from Vercel Dashboard → Storage → Blob → .env.local",
            token[:25],
        )
        # Don't raise — maybe Vercel changed the format; try anyway

    return token


def _scaffold() -> dict[str, list]:
    return {"news": [], "vulnerability": [], "fraud": [], "bug": []}
