"""
pipeline/enrichers/image_ai.py
================================
Generates cybersecurity-themed images via Hugging Face Inference API.

FIX (2026): Both previous models returned 410 Gone (permanently removed):
  ✗ stabilityai/stable-diffusion-2-1   → 410 Gone
  ✗ runwayml/stable-diffusion-v1-5     → 410 Gone

Replacement models (confirmed working, free tier):
  ✓ PRIMARY:  black-forest-labs/FLUX.1-schnell  (fast, high quality, free)
  ✓ FALLBACK: stabilityai/stable-diffusion-xl-base-1.0  (SDXL, free tier)
  ✓ FALLBACK2: prashanth970/flux-lora-uncensored (tiny FLUX variant, free)

FLUX.1-schnell uses a different payload format — it does NOT accept
"negative_prompt" or "guidance_scale". We handle both formats below.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.storage.blob import upload_image_to_blob
from pipeline.utils.helpers import get_logger

log = get_logger(__name__)

HF_URL         = "https://api-inference.huggingface.co/models/{model}"
IMAGE_TIMEOUT  = 60.0   # FLUX can take up to 45s on cold start

# Model list — tried in order until one succeeds
# Each entry: (model_id, supports_negative_prompt)
MODELS = [
    ("black-forest-labs/FLUX.1-schnell",             False),  # PRIMARY — fast & free
    ("stabilityai/stable-diffusion-xl-base-1.0",     True),   # FALLBACK — SDXL
    ("stabilityai/stable-diffusion-3-medium-diffusers", False), # FALLBACK2
]

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

    for model_id, supports_neg in MODELS:
        try:
            image_bytes = await _call_hf(full_prompt, model_id, hf_token, supports_neg)
            if image_bytes:
                log.info("[image_ai] Success with model '%s' for '%s'", model_id, item_id)
                break
        except Exception as exc:
            log.warning("[image_ai] Model '%s' failed for '%s': %s", model_id, item_id, exc)

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


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=5, max=15), reraise=True)
async def _call_hf(prompt: str, model: str, token: str, supports_negative: bool) -> bytes:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    # FLUX.1-schnell and newer models use a simpler payload
    if supports_negative:
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
    else:
        # FLUX format — minimal params only
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 4,   # FLUX.1-schnell is optimised for 1-4 steps
                "width":               512,
                "height":              512,
            },
            "options": {"wait_for_model": True, "use_cache": False},
        }

    async with httpx.AsyncClient(timeout=IMAGE_TIMEOUT) as client:
        r = await client.post(HF_URL.format(model=model), headers=headers, json=payload)
        if r.status_code == 503:
            wait = r.json().get("estimated_time", "?")
            raise RuntimeError(f"Model cold-starting, estimated wait={wait}s")
        if r.status_code == 410:
            raise RuntimeError(f"Model '{model}' has been removed from HuggingFace (410 Gone)")
        r.raise_for_status()

        # Validate we got image bytes, not a JSON error
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            raise RuntimeError(f"Unexpected content-type '{content_type}': {r.text[:200]}")

        return r.content


def _build_prompt(raw: str, category: str) -> str:
    prefix = CATEGORY_PREFIXES.get(category, "cybersecurity concept art,")
    suffix = ", cinematic lighting, dark moody atmosphere, ultra-detailed, 4k, no text, no people"
    return f"{prefix} {raw}{suffix}"
