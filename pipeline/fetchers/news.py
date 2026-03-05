"""
pipeline/fetchers/news.py
=========================
Fetches cybersecurity news from 5 free RSS feeds concurrently.

Sources (all free, no API key required):
  • The Hacker News    — https://feeds.feedburner.com/TheHackersNews
  • Bleeping Computer  — https://www.bleepingcomputer.com/feed/
  • SecurityWeek       — https://feeds.feedburner.com/securityweek
  • Krebs on Security  — https://krebsonsecurity.com/feed/
  • Dark Reading       — https://www.darkreading.com/rss.xml

Key design points:
  - feedparser is synchronous; asyncio.to_thread() keeps the event loop free.
  - Each feed is isolated — one failure doesn't affect others.
  - Items are deduplicated via SHA-256 ID before returning.
"""

from __future__ import annotations

import asyncio
from typing import Any

import feedparser

from pipeline.utils.helpers import get_logger, make_item_id, normalise_timestamp, sanitise_text

log = get_logger(__name__)

CATEGORY = "news"
MAX_ITEMS_PER_FEED = 5

RSS_FEEDS: list[tuple[str, str]] = [
    ("The Hacker News",   "https://feeds.feedburner.com/TheHackersNews"),
    ("Bleeping Computer", "https://www.bleepingcomputer.com/feed/"),
    ("SecurityWeek",      "https://feeds.feedburner.com/securityweek"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("Dark Reading",      "https://www.darkreading.com/rss.xml"),
]


async def fetch_news(existing_ids: set[str]) -> list[dict[str, Any]]:
    """
    Fetch all RSS feeds concurrently, return only items not in existing_ids.
    """
    tasks = [_fetch_single_feed(name, url, existing_ids) for name, url in RSS_FEEDS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_items: list[dict[str, Any]] = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            log.warning("[news] Feed '%s' failed: %s", RSS_FEEDS[idx][0], result)
        else:
            new_items.extend(result)  # type: ignore[arg-type]

    log.info("[news] %d new items from %d feeds", len(new_items), len(RSS_FEEDS))
    return new_items


async def _fetch_single_feed(
    name: str, url: str, existing_ids: set[str]
) -> list[dict[str, Any]]:
    try:
        feed = await asyncio.to_thread(
            feedparser.parse, url,
            request_headers={"User-Agent": "CyberIntelHub/2.0"},
        )
    except Exception as exc:
        raise RuntimeError(f"feedparser error: {exc}") from exc

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Malformed feed: {feed.bozo_exception}")

    items: list[dict[str, Any]] = []
    for entry in feed.entries[: MAX_ITEMS_PER_FEED * 2]:
        if len(items) >= MAX_ITEMS_PER_FEED:
            break

        link = getattr(entry, "link", "") or ""
        if not link:
            continue

        item_id = make_item_id(link, CATEGORY)
        if item_id in existing_ids:
            continue

        summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        )
        items.append({
            "id":             item_id,
            "category":       CATEGORY,
            "source":         name,
            "source_url":     link,
            "original_title": sanitise_text(getattr(entry, "title", "Untitled"), 200),
            "raw_summary":    sanitise_text(summary, 400),
            "timestamp":      normalise_timestamp(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            ),
        })
        existing_ids.add(item_id)

    return items
