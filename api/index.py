"""
api/index.py
============
Vercel serverless function — READ-ONLY public API.

FIX (2026): Vercel's @vercel/python runtime requires a plain
BaseHTTPRequestHandler subclass. FastAPI + Mangum causes:
  TypeError: issubclass() arg 1 must be a class
This version uses stdlib http.server only — zero extra dependencies.

Endpoints:
  GET /api/data    → Full data.json (CDN cached 60s)
  GET /api/health  → Item counts + last-modified timestamp
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler


BLOB_API = "https://blob.vercel-storage.com"
TIMEOUT  = 8


class handler(BaseHTTPRequestHandler):

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/data":
            self._serve_data()
        elif path == "/api/health":
            self._serve_health()
        else:
            self._send_json({"error": "Not found"}, status=404)

    # ── Endpoints ────────────────────────────────────────────────────────

    def _serve_data(self):
        try:
            data = self._load_data_json()
            self._send_json(
                data,
                extra_headers={
                    "Cache-Control": "public, s-maxage=60, stale-while-revalidate=120",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except EnvironmentError as exc:
            self._send_json({"error": str(exc)}, status=503)
        except Exception as exc:
            self._send_json({"error": f"Failed to load data: {exc}"}, status=500)

    def _serve_health(self):
        try:
            data = self._load_data_json()
            counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
            self._send_json({
                "status":    "ok",
                "counts":    counts,
                "total":     sum(counts.values()),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })
        except Exception as exc:
            self._send_json({"status": "degraded", "error": str(exc)})

    # ── Blob reader ──────────────────────────────────────────────────────

    def _load_data_json(self) -> dict:
        token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
        if not token:
            raise EnvironmentError(
                "BLOB_READ_WRITE_TOKEN is not configured in Vercel environment variables."
            )

        # Step 1: Find the CDN URL for data.json
        list_url = f"{BLOB_API}?prefix=data.json&limit=1"
        req = urllib.request.Request(
            list_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return self._scaffold()
            raise

        blobs = body.get("blobs", [])
        if not blobs:
            return self._scaffold()

        cdn_url = blobs[0]["url"]

        # Step 2: Fetch actual JSON from CDN
        with urllib.request.urlopen(cdn_url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())

    # ── Helpers ──────────────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200, extra_headers: dict = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # suppress default stderr logging
        pass

    @staticmethod
    def _scaffold() -> dict:
        return {"news": [], "vulnerability": [], "fraud": [], "bug": []}
