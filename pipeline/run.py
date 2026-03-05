"""
pipeline/run.py
===============
The standalone entry point executed by GitHub Actions.

This script is the "brain" of the entire CyberIntel Hub. It orchestrates:
  1. Loading existing data from Vercel Blob (for deduplication)
  2. Fetching new items from all sources concurrently
  3. Enriching each new item with Gemini text analysis + SD image
  4. Merging + pruning the master dataset
  5. Persisting the updated data.json back to Vercel Blob

Run locally:
    PYTHONPATH=. python pipeline/run.py

Run with forced re-process (ignore dedup):
    FORCE_REFRESH=true PYTHONPATH=. python pipeline/run.py

Exit codes:
    0 — success (including "no new items" runs)
    1 — fatal error (missing token, complete fetch failure, etc.)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Bootstrap logging FIRST so all modules inherit it ─────────────────────────
# We write to both stdout (for GitHub Actions live log) and a .log file
# (uploaded as a workflow artifact for post-run debugging).

LOG_FILE = "pipeline_run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("pipeline.run")

# ── Local imports (after path is set via PYTHONPATH=.) ────────────────────────
from pipeline.fetchers.news       import fetch_news
from pipeline.fetchers.vulns      import fetch_vulnerabilities
from pipeline.fetchers.fraud_bugs import fetch_bugs, fetch_fraud
from pipeline.enrichers.text_ai   import enrich_item_text
from pipeline.enrichers.image_ai  import generate_and_upload_image
from pipeline.storage.blob        import load_data_json, save_data_json
from pipeline.utils.helpers       import extract_existing_ids

# ── Pipeline configuration ─────────────────────────────────────────────────────
MAX_NEW_ITEMS_PER_RUN  = 15    # Cap to avoid timeout / rate-limit blowout
MAX_AGE_DAYS           = 30    # Prune items older than this from data.json
MAX_CONCURRENT_AI      = 3     # Semaphore limit for concurrent AI calls
FORCE_REFRESH          = os.getenv("FORCE_REFRESH", "false").lower() == "true"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ASYNC PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> dict[str, Any]:
    run_start = time.monotonic()
    log.info("=" * 70)
    log.info("CyberIntel Hub — Pipeline Starting")
    log.info("Timestamp : %s", datetime.now(tz=timezone.utc).isoformat())
    log.info("Force mode: %s", FORCE_REFRESH)
    log.info("=" * 70)

    # ── Validate required env vars before doing any work ──────────────────
    _validate_environment()

    # ── Step 1: Load existing data.json ───────────────────────────────────
    log.info("STEP 1/5 — Loading existing data from Vercel Blob...")
    existing_data = await load_data_json()
    existing_ids: set[str] = set() if FORCE_REFRESH else extract_existing_ids(existing_data)
    log.info("  Existing items: %d  |  Dedup IDs loaded: %d",
             sum(len(v) for v in existing_data.values() if isinstance(v, list)),
             len(existing_ids))

    # ── Step 2: Fetch from all sources concurrently ────────────────────────
    log.info("STEP 2/5 — Fetching from all intelligence sources...")
    news_items, vuln_items, fraud_items, bug_items = await asyncio.gather(
        fetch_news(existing_ids),
        fetch_vulnerabilities(existing_ids),
        fetch_fraud(existing_ids),
        fetch_bugs(existing_ids),
        return_exceptions=False,
    )

    all_new = news_items + vuln_items + fraud_items + bug_items
    log.info("  Raw new items: news=%d  vulns=%d  fraud=%d  bugs=%d  total=%d",
             len(news_items), len(vuln_items), len(fraud_items), len(bug_items), len(all_new))

    # Apply hard cap and log what gets dropped
    if len(all_new) > MAX_NEW_ITEMS_PER_RUN:
        log.info("  Capping to %d items (dropping %d)", MAX_NEW_ITEMS_PER_RUN, len(all_new) - MAX_NEW_ITEMS_PER_RUN)
        all_new = all_new[:MAX_NEW_ITEMS_PER_RUN]

    if not all_new:
        elapsed = time.monotonic() - run_start
        log.info("✅ No new items found. Pipeline finished in %.1fs", elapsed)
        return {"status": "ok", "new_items": 0, "elapsed_seconds": round(elapsed, 2)}

    # ── Step 3: AI enrichment ──────────────────────────────────────────────
    log.info("STEP 3/5 — Enriching %d items with AI (text + image)...", len(all_new))
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_AI)
    enriched_items = await _enrich_all(all_new, semaphore)
    log.info("  Successfully enriched: %d / %d", len(enriched_items), len(all_new))

    # ── Step 4: Merge + prune ─────────────────────────────────────────────
    log.info("STEP 4/5 — Merging new items into dataset and pruning old entries...")
    updated_data = _merge_and_prune(existing_data, enriched_items)
    for cat, items in updated_data.items():
        log.info("  %-15s : %d items", cat, len(items))

    # ── Step 5: Persist to Vercel Blob ─────────────────────────────────────
    log.info("STEP 5/5 — Saving data.json to Vercel Blob...")
    blob_url = await save_data_json(updated_data)
    log.info("  Saved → %s", blob_url)

    elapsed = time.monotonic() - run_start
    summary = {
        "status":          "ok",
        "new_items":       len(enriched_items),
        "by_category":     _count_by_category(enriched_items),
        "total_in_store":  {k: len(v) for k, v in updated_data.items() if isinstance(v, list)},
        "blob_url":        blob_url,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp":       datetime.now(tz=timezone.utc).isoformat(),
    }
    log.info("=" * 70)
    log.info("✅ Pipeline complete in %.1fs", elapsed)
    log.info("   Summary: %s", json.dumps(summary, indent=2))
    log.info("=" * 70)
    return summary


# ══════════════════════════════════════════════════════════════════════════════
# AI Enrichment Orchestration
# ══════════════════════════════════════════════════════════════════════════════

async def _enrich_all(items: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """
    Enrich every item with text AI + image AI concurrently.
    The semaphore prevents hammering free-tier APIs.
    Failed items are skipped (logged as errors) rather than aborting the run.
    """
    async def _enrich_one(item: dict, idx: int) -> dict | None:
        async with semaphore:
            item_label = f"[{idx+1}/{len(items)}] {item.get('id', '?')} ({item.get('category')})"
            try:
                log.info("  Enriching %s ...", item_label)

                # A: Text analysis via Gemini / Groq
                enriched = await enrich_item_text(item)

                # B: Image generation via Hugging Face → upload to Blob
                image_url = await generate_and_upload_image(
                    item_id=item["id"],
                    image_prompt=enriched.get("image_prompt", ""),
                    category=item.get("category", "news"),
                )

                enriched["image_path"] = image_url
                enriched.pop("image_prompt", None)   # Internal field — don't expose
                enriched.pop("raw_summary", None)    # Verbose — not needed in output

                log.info("  ✓ Done %s", item_label)
                return enriched

            except Exception as exc:
                log.error("  ✗ Failed %s: %s", item_label, exc, exc_info=True)
                return None

    tasks = [_enrich_one(item, i) for i, item in enumerate(items)]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


# ══════════════════════════════════════════════════════════════════════════════
# Data Management
# ══════════════════════════════════════════════════════════════════════════════

def _merge_and_prune(existing: dict[str, list], new_items: list[dict]) -> dict[str, list]:
    """
    Prepend new items to their respective category lists.
    Remove items older than MAX_AGE_DAYS.
    Enforce a per-category maximum of 200 items (memory safety).
    """
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    MAX_PER_CATEGORY = 200

    # Group new items by category
    by_cat: dict[str, list] = {"news": [], "vulnerability": [], "fraud": [], "bug": []}
    for item in new_items:
        cat = item.get("category", "news")
        if cat in by_cat:
            by_cat[cat].append(item)

    updated: dict[str, list] = {}
    for cat in by_cat:
        combined = by_cat[cat] + existing.get(cat, [])
        # Prune old items
        pruned = [i for i in combined if i.get("timestamp", "9999") >= cutoff]
        # Cap at max to control blob size
        updated[cat] = pruned[:MAX_PER_CATEGORY]

    return updated


def _count_by_category(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        cat = item.get("category", "unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


# ══════════════════════════════════════════════════════════════════════════════
# Environment Validation
# ══════════════════════════════════════════════════════════════════════════════

def _validate_environment() -> None:
    """
    Fail fast with a clear error if critical secrets are missing.
    This prevents wasting GitHub Actions minutes on a doomed run.
    """
    errors = []

    if not os.getenv("BLOB_READ_WRITE_TOKEN"):
        errors.append("BLOB_READ_WRITE_TOKEN — required for Vercel Blob storage")

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
        errors.append("GEMINI_API_KEY or GROQ_API_KEY — at least one text AI key required")

    if errors:
        log.critical("❌ Missing required environment variables:")
        for e in errors:
            log.critical("   • %s", e)
        log.critical("Set these in: GitHub → Repo → Settings → Secrets → Actions")
        sys.exit(1)

    log.info("Environment validation passed ✓")
    log.info("  BLOB:   %s", "✓ set" if os.getenv("BLOB_READ_WRITE_TOKEN") else "✗ missing")
    log.info("  GEMINI: %s", "✓ set" if os.getenv("GEMINI_API_KEY") else "— not set (Groq fallback)")
    log.info("  GROQ:   %s", "✓ set" if os.getenv("GROQ_API_KEY") else "— not set")
    log.info("  HF:     %s", "✓ set" if os.getenv("HF_API_TOKEN") else "— not set (SVG placeholders)")


# ══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        log.info("Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        log.critical("💥 Pipeline crashed with unhandled exception: %s", exc, exc_info=True)
        sys.exit(1)
