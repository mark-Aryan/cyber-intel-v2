"""
pipeline/enrichers/text_ai.py
==============================
AI text enrichment: Google Gemini 2.0 Flash (primary) → Groq Llama-3 (fallback).

FIX (2026):
  - gemini-1.5-flash → removed from v1beta API, replaced with gemini-2.0-flash
  - groq model updated to llama-3.3-70b-versatile (llama3-8b-8192 deprecated)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.utils.helpers import get_logger

log = get_logger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"           # FIX: was gemini-1.5-flash (404)
GROQ_MODEL   = "llama-3.3-70b-versatile"    # FIX: was llama3-8b-8192 (deprecated)
MAX_TOKENS   = 700

PROMPT_TEMPLATE = """
You are a senior cybersecurity analyst. Analyse the following item and respond with ONLY a valid JSON object — no markdown fences, no preamble, no trailing text.

Category: {category}
Source: {source}
Title: {original_title}
Summary: {raw_summary}

Return EXACTLY this JSON structure (every field is required):
{{
  "In-Depth Detail": {{
    "executive_summary": "<2-3 plain-English sentences for a non-technical audience>",
    "technical_analysis": "<3-5 sentences for security engineers — include CVE refs, attack vectors, affected versions if known>",
    "impact": "<Which systems, users, or sectors are affected and how severely?>",
    "root_cause": "<What underlying weakness or design flaw enabled this?>",
    "mitigation": "<Specific, actionable steps defenders can take immediately>",
    "severity_rating": "<one of: CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>",
    "affected_technologies": ["<tech1>", "<tech2>"],
    "ioc_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]
  }},
  "image_prompt": "<20-word max Stable Diffusion prompt — purely visual, no text/logos/faces in image>"
}}
""".strip()


async def enrich_item_text(item: dict[str, Any]) -> dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        category=item.get("category", "unknown"),
        source=item.get("source", "unknown"),
        original_title=item.get("original_title", ""),
        raw_summary=item.get("raw_summary", ""),
    )

    result: dict | None = None

    if os.getenv("GEMINI_API_KEY"):
        try:
            result = await _call_gemini(prompt, os.environ["GEMINI_API_KEY"])
        except Exception as exc:
            log.warning("[text_ai] Gemini failed for '%s': %s → trying Groq", item.get("id"), exc)

    if result is None and os.getenv("GROQ_API_KEY"):
        try:
            result = await _call_groq(prompt, os.environ["GROQ_API_KEY"])
        except Exception as exc:
            log.error("[text_ai] Groq also failed for '%s': %s", item.get("id"), exc)

    if result is None:
        log.warning("[text_ai] Both providers failed for '%s' — using placeholder", item.get("id"))
        result = _placeholder(item)

    return {
        **item,
        "In-Depth Detail": result.get("In-Depth Detail", {}),
        "image_prompt": result.get(
            "image_prompt",
            f"abstract cybersecurity threat visualization dark background {item.get('category', '')}",
        ),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8), reraise=True)
async def _call_gemini(prompt: str, api_key: str) -> dict:
    import google.generativeai as genai

    def _sync() -> str:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        return model.generate_content(prompt).text

    return _parse_json(await asyncio.to_thread(_sync))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8), reraise=True)
async def _call_groq(prompt: str, api_key: str) -> dict:
    from groq import Groq

    def _sync() -> str:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a cybersecurity analyst. Respond ONLY with valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content

    return _parse_json(await asyncio.to_thread(_sync))


def _parse_json(raw: str) -> dict:
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean.strip())
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Cannot parse AI response as JSON: {clean[:200]}")


def _placeholder(item: dict) -> dict:
    return {
        "In-Depth Detail": {
            "executive_summary":     item.get("raw_summary", "No summary available."),
            "technical_analysis":    "AI enrichment temporarily unavailable.",
            "impact":                "Unknown — please refer to the source URL.",
            "root_cause":            "Analysis pending.",
            "mitigation":            "Monitor the source URL for official guidance.",
            "severity_rating":       item.get("severity", "UNKNOWN"),
            "affected_technologies": [],
            "ioc_keywords":          [],
        },
        "image_prompt": "cyber threat network abstract dark glowing nodes digital",
    }
