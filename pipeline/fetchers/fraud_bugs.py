"""
pipeline/fetchers/fraud_bugs.py
================================
Fetches Cyber Fraud alerts and Software Bug advisories from free RSS/Atom feeds.

Fraud sources:  CISA, FTC Consumer Alerts, IC3 (FBI)
Bug sources:    GitHub Security Advisories, CERT/CC, Exploit-DB, Mozilla
"""

from __future__ import annotations

import asyncio
from typing import Any

import feedparser

from pipeline.utils.helpers import get_logger, make_item_id, normalise_timestamp, sanitise_text

log = get_logger(__name__)
MAX_ITEMS_PER_FEED = 4

FRAUD_FEEDS: list[tuple[str, str]] = [
    ("CISA Alerts",   "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("FTC Consumer",  "https://consumer.ftc.gov/consumer-alerts/rss"),
    ("IC3 FBI Cyber", "https://www.ic3.gov/Media/news/rss"),
]

BUG_FEEDS: list[tuple[str, str]] = [
    ("GitHub Advisories", "https://github.com/advisories.atom"),
    ("CERT/CC Vulns",     "https://kb.cert.org/vuls/atomfeed/"),
    ("Exploit-DB",        "https://www.exploit-db.com/rss.xml"),
    ("Mozilla Security",  "https://www.mozilla.org/en-US/security/advisories/feed/"),
]


async def fetch_fraud(existing_ids: set[str]) -> list[dict[str, Any]]:
    items = await _gather_feeds(FRAUD_FEEDS, "fraud", existing_ids)
    log.info("[fraud] %d new fraud items", len(items))
    return items


async def fetch_bugs(existing_ids: set[str]) -> list[dict[str, Any]]:
    items = await _gather_feeds(BUG_FEEDS, "bug", existing_ids)
    log.info("[bugs] %d new bug items", len(items))
    return items


async def _gather_feeds(
    feed_list: list[tuple[str, str]], category: str, existing_ids: set[str]
) -> list[dict[str, Any]]:
    tasks   = [_fetch_single_feed(name, url, category, existing_ids) for name, url in feed_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: list[dict[str, Any]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log.warning("[%s] Feed '%s' failed: %s", category, feed_list[i][0], result)
        else:
            items.extend(result)  # type: ignore[arg-type]
    return items


async def _fetch_single_feed(
    name: str, url: str, category: str, existing_ids: set[str]
) -> list[dict[str, Any]]:
    try:
        feed = await asyncio.to_thread(
            feedparser.parse, url,
            request_headers={"User-Agent": "CyberIntelHub/2.0"},
        )
    except Exception as exc:
        raise RuntimeError(f"feedparser failed for '{name}': {exc}") from exc

    items: list[dict[str, Any]] = []
    for entry in feed.entries[: MAX_ITEMS_PER_FEED * 2]:
        if len(items) >= MAX_ITEMS_PER_FEED:
            break

        link = getattr(entry, "link", "") or getattr(entry, "id", "") or ""
        if not link:
            continue

        item_id = make_item_id(link, category)
        if item_id in existing_ids:
            continue

        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or content
        )

        items.append({
            "id":             item_id,
            "category":       category,
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
