"""
pipeline/fetchers/vulns.py
==========================
Fetches recent HIGH/CRITICAL CVEs from the NIST NVD REST API v2.0.
Free — no API key required (optional key raises rate limit from 5→50 req/30s).

API docs: https://nvd.nist.gov/developers/vulnerabilities

Filters applied:
  - CVSS v3 severity: HIGH or CRITICAL only (score >= 7.0)
  - Published within the last LOOKBACK_DAYS
  - Maximum MAX_VULNS new items returned per run
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.utils.helpers import get_logger, make_item_id, normalise_timestamp, sanitise_text

log = get_logger(__name__)

CATEGORY         = "vulnerability"
MAX_VULNS        = 10
LOOKBACK_DAYS    = 2
NVD_API_URL      = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_TIMEOUT      = 20.0   # NVD can be slow — GitHub Actions has no 10s limit!


async def fetch_vulnerabilities(existing_ids: set[str]) -> list[dict[str, Any]]:
    """Fetch new high/critical CVEs from the last LOOKBACK_DAYS."""
    try:
        raw_cves = await _fetch_nvd_cves()
    except Exception as exc:
        log.error("[vulns] NVD fetch failed entirely: %s", exc)
        return []

    items: list[dict[str, Any]] = []
    for cve in raw_cves:
        if len(items) >= MAX_VULNS:
            break

        cve_id = _extract_cve_id(cve)
        if not cve_id:
            continue

        url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        item_id = make_item_id(url, CATEGORY)
        if item_id in existing_ids:
            continue

        score    = _extract_cvss_score(cve)
        severity = _score_to_severity(score)

        items.append({
            "id":             item_id,
            "category":       CATEGORY,
            "source":         "NIST NVD",
            "source_url":     url,
            "original_title": f"{cve_id} — {severity} ({score})",
            "raw_summary":    sanitise_text(_extract_description(cve), 400),
            "timestamp":      normalise_timestamp(_extract_published(cve)),
            "cvss_score":     score,
            "severity":       severity,
        })
        existing_ids.add(item_id)

    log.info("[vulns] %d new CVEs from NVD", len(items))
    return items


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8), reraise=True)
async def _fetch_nvd_cves() -> list[dict]:
    now   = datetime.now(tz=timezone.utc)
    start = now - timedelta(days=LOOKBACK_DAYS)
    params = {
        "pubStartDate":   start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":     now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "cvssV3Severity": "HIGH",
        "resultsPerPage": MAX_VULNS * 2,
    }
    async with httpx.AsyncClient(timeout=NVD_TIMEOUT) as client:
        r = await client.get(NVD_API_URL, params=params,
                             headers={"User-Agent": "CyberIntelHub/2.0"})
        r.raise_for_status()
        return r.json().get("vulnerabilities", [])


def _extract_cve_id(v: dict) -> str | None:
    try:    return v["cve"]["id"]
    except: return None

def _extract_description(v: dict) -> str:
    try:
        for d in v["cve"]["descriptions"]:
            if d.get("lang") == "en": return d.get("value", "")
        return v["cve"]["descriptions"][0].get("value", "")
    except: return ""

def _extract_cvss_score(v: dict) -> float:
    try:
        m = v["cve"]["metrics"]
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in m and m[key]:
                return float(m[key][0]["cvssData"]["baseScore"])
    except: pass
    return 0.0

def _extract_published(v: dict) -> str | None:
    try:    return v["cve"].get("published")
    except: return None

def _score_to_severity(s: float) -> str:
    if s >= 9.0: return "CRITICAL"
    if s >= 7.0: return "HIGH"
    if s >= 4.0: return "MEDIUM"
    if s >  0.0: return "LOW"
    return "UNKNOWN"
