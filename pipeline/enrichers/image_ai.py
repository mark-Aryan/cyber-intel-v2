"""
pipeline/enrichers/image_ai.py
================================
Generates cybersecurity-themed images via Hugging Face Inference API
(Stable Diffusion 2.1 — free tier, ~1,000 req/day).

Key difference from the Vercel version:
  - GitHub Actions has no 10-second timeout, so we use a 30-second
    client timeout and allow the model warm-up wait.
  - We try the primary model, fall back to the secondary, then return
    a category-specific SVG placeholder path on total failure.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.storage.blob import upload_image_to_blob
from pipeline.utils.helpers import get_logger

log = get_logger(__name__)

HF_URL          = "https://api-inference.huggingface.co/models/{model}"
PRIMARY_MODEL   = "stabilityai/stable-diffusion-2-1"
FALLBACK_MODEL  = "runwayml/stable-diffusion-v1-5"
IMAGE_TIMEOUT   = 30.0   # GitHub Actions can afford to wait longer

NEGATIVE_PROMPT = (
    "text, words, watermark, logo, nsfw, cartoon, anime, "
    "blurry, low quality, ugly, deformed, people faces, humans"
)

FALLBACK_IMAGES = {
    "news":          "/placeholders/news.svg",
    "vulnerability": "/placeholders/vulnerability.svg",
    "fraud":         "/placeholders/fraud.svg",
    "bug":           "/placeholders/bug.svg",
}

CATEGORY_PREFIXES = {
    "news":          "digital cybersecurity abstract concept art,",
    "vulnerability": "glowing exploit code vulnerability cyber attack,",
    "fraud":         "dark web phishing digital fraud network,",
    "bug":           "binary code software error matrix visualization,",
}


async def generate_and_upload_image(
    item_id: str, image_prompt: str, category: str
) -> str:
    """
    Generate an image for this item and upload to Vercel Blob.
    Returns the public CDN URL, or an SVG placeholder path on failure.
    """
    hf_token = os.getenv("HF_API_TOKEN")
    if not hf_token:
        log.info("[image_ai] HF_API_TOKEN not set — using placeholder for '%s'", item_id)
        return FALLBACK_IMAGES.get(category, "/placeholders/news.svg")

    full_prompt = _build_prompt(image_prompt, category)
    image_bytes: bytes | None = None

    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            image_bytes = await _call_hf(full_prompt, model, hf_token)
            if image_bytes:
                break
        except Exception as exc:
            log.warning("[image_ai] Model '%s' failed for '%s': %s", model, item_id, exc)

    if not image_bytes:
        log.warning("[image_ai] All models failed for '%s' — using placeholder", item_id)
        return FALLBACK_IMAGES.get(category, "/placeholders/news.svg")

    try:
        url = await upload_image_to_blob(f"images/{category}/{item_id}.png", image_bytes)
        log.info("[image_ai] Uploaded image → %s", url)
        return url
    except Exception as exc:
        log.error("[image_ai] Blob upload failed for '%s': %s", item_id, exc)
        return FALLBACK_IMAGES.get(category, "/placeholders/news.svg")


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=3, max=10), reraise=True)
async def _call_hf(prompt: str, model: str, token: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt":     NEGATIVE_PROMPT,
            "num_inference_steps": 25,
            "guidance_scale":      7.5,
            "width":               512,
            "height":              512,
        },
        "options": {"wait_for_model": True, "use_cache": False},
    }
    async with httpx.AsyncClient(timeout=IMAGE_TIMEOUT) as client:
        r = await client.post(HF_URL.format(model=model), headers=headers, json=payload)
        if r.status_code == 503:
            wait = r.json().get("estimated_time", "?")
            raise RuntimeError(f"Model cold-starting, wait={wait}s")
        r.raise_for_status()
        return r.content


def _build_prompt(raw: str, category: str) -> str:
    prefix = CATEGORY_PREFIXES.get(category, "cybersecurity concept art,")
    suffix = ", cinematic lighting, dark moody atmosphere, ultra-detailed, 4k"
    return f"{prefix} {raw}{suffix}"
