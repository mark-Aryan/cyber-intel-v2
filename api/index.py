"""
api/index.py
============
Vercel serverless function — READ-ONLY public API.

This is deliberately minimal: it has exactly ONE job — read data.json from
Vercel Blob and serve it to the frontend. ALL the heavy lifting (fetching,
AI enrichment, storage writes) now happens in GitHub Actions.

Endpoints:
  GET /api/data    → Full data.json (cached 60s at CDN edge)
  GET /api/health  → Item counts + last-modified timestamp

Because this endpoint only does a single Blob GET request, it will complete
well within Vercel's 10-second timeout on the free Hobby plan.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CyberIntel Hub — Public API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

handler = Mangum(app, lifespan="off")

BLOB_API  = "https://blob.vercel-storage.com"
TIMEOUT   = 8.0


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/data")
async def get_data() -> JSONResponse:
    """
    Serve the master intelligence feed to the frontend.
    CDN cache: 60s fresh, 120s stale-while-revalidate.
    """
    try:
        data = await _load_data_json()
        return JSONResponse(
            content=data,
            headers={
                "Cache-Control": "public, s-maxage=60, stale-while-revalidate=120",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load data: {exc}")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Lightweight health check — returns item counts."""
    try:
        data = await _load_data_json()
        counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
        return {
            "status":    "ok",
            "counts":    counts,
            "total":     sum(counts.values()),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


# ── Blob reader ────────────────────────────────────────────────────────────────

async def _load_data_json() -> dict[str, Any]:
    token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not token:
        raise EnvironmentError(
            "BLOB_READ_WRITE_TOKEN is not configured in Vercel environment variables."
        )

    # Step 1: Find the CDN URL for data.json
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        list_r = await client.get(
            f"{BLOB_API}?prefix=data.json&limit=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        if list_r.status_code == 404:
            return _scaffold()
        list_r.raise_for_status()

        blobs = list_r.json().get("blobs", [])
        if not blobs:
            return _scaffold()

        cdn_url = blobs[0]["url"]

    # Step 2: Fetch the actual JSON content from CDN
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data_r = await client.get(cdn_url)
        data_r.raise_for_status()
        return data_r.json()


def _scaffold() -> dict[str, list]:
    return {"news": [], "vulnerability": [], "fraud": [], "bug": []}
