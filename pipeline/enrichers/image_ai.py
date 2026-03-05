"""
pipeline/enrichers/image_ai.py
================================
Generates cybersecurity-themed images via Hugging Face Inference Providers.

ROOT CAUSE OF ALL PREVIOUS FAILURES (2026):
  ✗  stabilityai/stable-diffusion-2-1   → 410 Gone (permanently removed)
  ✗  runwayml/stable-diffusion-v1-5     → 410 Gone (permanently removed)
  ✗  Raw httpx POST to api-inference.huggingface.co → wrong API entirely

  HuggingFace replaced the old Inference API with "Inference Providers" in
  2025. The correct method is the huggingface_hub AsyncInferenceClient SDK
  which handles routing, auth, and provider selection automatically.

PRIMARY MODEL : black-forest-labs/FLUX.1-schnell  (free tier, ~4 steps, fast)
FALLBACK MODEL: stabilityai/stable-diffusion-3.5-large-turbo (free tier)

REQUIRES: huggingface_hub>=0.23.0, Pillow — both added to requirements-pipeline.txt
"""

from __future__ import annotations

import asyncio
import io
import os

from pipeline.storage.blob import upload_image_to_blob
from pipeline.utils.helpers import get_logger

log = get_logger(__name__)

MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-3.5-large-turbo",
]

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
    Generate an image and upload to Vercel Blob.
    Returns the public CDN URL, or a local SVG placeholder path on failure.
    """
    hf_token = os.getenv("HF_API_TOKEN", "").strip()
    if not hf_token:
        log.info("[image_ai] HF_API_TOKEN not set — using placeholder for '%s'", item_id)
        return FALLBACK_IMAGES.get(category, "/placeholders/news.svg")

    full_prompt = _build_prompt(image_prompt, category)
    image_bytes: bytes | None = None

    for model in MODELS:
        try:
            image_bytes = await _generate_image(full_prompt, model, hf_token)
            if image_bytes:
                log.info("[image_ai] Generated image with '%s' for '%s'", model, item_id)
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


async def _generate_image(prompt: str, model: str, token: str) -> bytes:
    """
    Use huggingface_hub AsyncInferenceClient — the correct 2026 API.
    Returns raw PNG bytes.
    """
    from huggingface_hub import AsyncInferenceClient

    client = AsyncInferenceClient(api_key=token)

    # Returns a PIL.Image object directly
    pil_image = await client.text_to_image(
        prompt=prompt,
        model=model,
    )

    # Convert PIL Image → PNG bytes for Blob upload
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


def _build_prompt(raw: str, category: str) -> str:
    prefix = CATEGORY_PREFIXES.get(category, "cybersecurity concept art,")
    suffix = ", cinematic lighting, dark moody atmosphere, ultra-detailed, 4k, no text, no people"
    return f"{prefix} {raw}{suffix}"
