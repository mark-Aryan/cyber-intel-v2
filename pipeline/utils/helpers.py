"""
pipeline/utils/helpers.py
=========================
Shared utility functions: logging, ID generation, timestamp normalisation,
text sanitisation, and JSON serialisation helpers.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-level logger.
    The root logger is already configured in pipeline/run.py,
    so all child loggers automatically inherit its handlers.
    """
    return logging.getLogger(name)


def make_item_id(source_url: str, category: str) -> str:
    """
    Generate a stable 16-char hex ID from URL + category.
    This is the deduplication key — same URL always produces same ID.
    """
    raw = f"{category}::{source_url.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalise_timestamp(raw: str | None) -> str:
    """
    Parse any date string format (RFC-2822, ISO-8601, RSS pubDate, etc.)
    and return a UTC ISO-8601 string.  Falls back to current UTC time.
    """
    if not raw:
        return _now_utc_iso()
    try:
        dt = date_parser.parse(raw, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError):
        return _now_utc_iso()


def _now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitise_text(text: str, max_chars: int = 400) -> str:
    """Strip HTML tags, collapse whitespace, truncate."""
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_chars]


def safe_json_default(obj: Any) -> str:
    """json.dumps() default handler for non-serialisable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def extract_existing_ids(data_json: dict) -> set[str]:
    """
    Walk the master data.json and return all stored item IDs as a flat set.
    Used by every fetcher to skip already-processed items in O(1).
    """
    ids: set[str] = set()
    for category_items in data_json.values():
        if isinstance(category_items, list):
            for item in category_items:
                if isinstance(item, dict) and "id" in item:
                    ids.add(item["id"])
    return ids
