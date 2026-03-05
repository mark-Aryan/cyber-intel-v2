<div align="center">

<!-- ═══════════════════════  TOP BANNER  ═══════════════════════ -->
<img src="https://capsule-render.vercel.app/api?type=venom&height=300&color=0:050509,50:0a1628,100:001a0a&text=CyberIntel%20Hub&fontSize=78&fontColor=00ff88&stroke=00ff88&strokeWidth=1.5&desc=Real-Time%20AI-Powered%20Cybersecurity%20Intelligence&descSize=19&descAlignY=74&descColor=8892a4&animation=fadeIn" width="100%"/>

<!-- ═══════════════════════  BADGE ROW 1  ═══════════════════════ -->
<p>
  <a href="https://cyberintelv2.vercel.app/">
    <img src="https://img.shields.io/badge/🛡%20Live%20Demo-cyberintelv2.vercel.app-00ff88?style=for-the-badge&labelColor=0a0a10"/>
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Version-v2.0-00e5ff?style=for-the-badge&labelColor=0a0a10"/>
  &nbsp;
  <img src="https://img.shields.io/badge/License-MIT-00ff88?style=for-the-badge&labelColor=0a0a10"/>
</p>

<!-- ═══════════════════════  BADGE ROW 2  ═══════════════════════ -->
<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Gemini-2.0--flash-4285F4?style=flat-square&logo=google&logoColor=white"/>
  &nbsp;
  <img src="https://img.shields.io/badge/FLUX.1--schnell-HuggingFace-FFD21E?style=flat-square&logo=huggingface&logoColor=black"/>
  &nbsp;
  <img src="https://img.shields.io/badge/GitHub_Actions-Cron%20Pipeline-2088FF?style=flat-square&logo=githubactions&logoColor=white"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Vercel-Blob%20%2B%20Serverless-000000?style=flat-square&logo=vercel&logoColor=white"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Cost-$0.00%2Fmonth-00ff88?style=flat-square"/>
</p>

<!-- ═══════════════════════  AUTHOR CHIPS  ═══════════════════════ -->
<p>
  <a href="https://codexploit.in/">
    <img src="https://img.shields.io/badge/Built%20by-Aryan%20Kumar%20Upadhyay%20(codeXploit)-00e5ff?style=flat-square&logo=hackthebox&logoColor=black"/>
  </a>
  &nbsp;
  <a href="https://github.com/mark-Aryan">
    <img src="https://img.shields.io/badge/GitHub-mark--Aryan-181717?style=flat-square&logo=github"/>
  </a>
  &nbsp;
  <a href="https://www.linkedin.com/in/aryan-kumar-upadhyay">
    <img src="https://img.shields.io/badge/LinkedIn-aryan--kumar--upadhyay-0A66C2?style=flat-square&logo=linkedin"/>
  </a>
  &nbsp;
  <a href="https://www.fiverr.com/mark_aryan">
    <img src="https://img.shields.io/badge/Hire%20Me-Fiverr%3A%20mark__aryan-1DBF73?style=flat-square&logo=fiverr&logoColor=white"/>
  </a>
</p>

</div>

---

## 📌 Table of Contents

- [What Is CyberIntel Hub?](#-what-is-cyberintel-hub)
- [Architecture](#-architecture)
- [Why GitHub Actions?](#-why-github-actions-instead-of-vercel-cron)
- [AI Stack](#-ai-stack)
- [Project Structure](#-project-structure)
- [Deployment Guide](#-deployment-guide)
  - [Step 1 — Get API Keys](#step-1--get-your-api-keys-all-free)
  - [Step 2 — Deploy to Vercel](#step-2--deploy-to-vercel)
  - [Step 3 — Set GitHub Secrets](#step-3--set-github-secrets)
  - [Step 4 — Push to GitHub](#step-4--push-to-github)
  - [Step 5 — Test Everything](#step-5--test-everything)
- [Local Development](#-local-development)
- [Configuration](#-configuration)
- [Monitoring & Maintenance](#-monitoring--maintenance)
- [Troubleshooting](#-troubleshooting)
- [Free Tier Usage](#-free-tier-usage)
- [Contributing](#-contributing)
- [Author](#-author)

---

## 🛡 What Is CyberIntel Hub?

**CyberIntel Hub** is a fully automated, AI-enriched cybersecurity intelligence platform. Every **30 minutes**, a GitHub Actions pipeline fetches live CVEs, fraud alerts, and security news — enriches each item with **Gemini 2.0-flash** analysis and a **FLUX.1-schnell** AI-generated image — then stores the result to Vercel Blob CDN for near-instant serving.

**No servers. No maintenance. No bills.**

| 🔴 Live Sources | 🤖 AI Layer | ☁️ Infrastructure |
|:---:|:---:|:---:|
| NIST NVD CVE API | Gemini 2.0-flash (primary) | GitHub Actions (automation) |
| 5 security RSS feeds | Groq Llama-3.3 (fallback) | Vercel Blob (storage + CDN) |
| CISA · FTC · IC3 Fraud | FLUX.1-schnell (images) | Vercel Hobby (frontend + API) |
| GitHub Advisories · CERT/CC | SHA-256 deduplication | Python stdlib serverless API |

---

## 🏗 Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║  ⚡  GITHUB ACTIONS  —  cron: every 30 minutes                       ║
║                                                                      ║
║  python pipeline/run.py                                              ║
║    │                                                                 ║
║    ├─ fetch_news()            ←  5 RSS feeds (async, concurrent)     ║
║    ├─ fetch_vulnerabilities() ←  NIST NVD CVE API  (HIGH/CRITICAL)   ║
║    ├─ fetch_fraud()           ←  CISA · FTC Consumer · IC3 FBI       ║
║    └─ fetch_bugs()            ←  GitHub Advisories · CERT/CC         ║
║         │                                                            ║
║         ▼  SHA-256 dedup — already-seen items are skipped            ║
║    ├─ enrich_item_text()      ←  Gemini 2.0-flash  →  Groq fallback  ║
║    ├─ generate_image()        ←  FLUX.1-schnell  (HuggingFace SDK)   ║
║    └─ save_data_json()  ──────────────────────────────────────────┐  ║
╚══════════════════════════════════════════════════════════════════ │ ═╝
                                                                    │
                                                    ☁️  Vercel Blob CDN
                                                          data.json
                                                          images/
                                                                    │
╔═══════════════════════════════════════════════════════════════════│══╗
║  🌐  VERCEL  —  always-on, read-only, zero AI calls               │  ║
║                                                                   │  ║
║  GET /api/data    ─── reads ─────────────────────────────────────┘  ║
║  GET /api/health  ─── counts + last-updated timestamp               ║
║                                                                      ║
║  /public/index.html  ←  polls /api/data every 60 seconds            ║
╚══════════════════════════════════════════════════════════════════════╝
```

> **Key design principle:** Vercel is a **read-only CDN wrapper**. All heavy lifting — AI calls, image generation, data writing — happens inside GitHub Actions where timeouts are measured in hours, not seconds.

---

## ⚡ Why GitHub Actions Instead of Vercel Cron?

<div align="center">

| Feature | Vercel Hobby Cron | GitHub Actions |
|:---|:---:|:---:|
| **Schedule frequency** | Daily only | Any interval — we use every 30 min ✅ |
| **Execution timeout** | 10 seconds | 6 hours ✅ |
| **Free minutes** | — | 2,000 min/month ✅ |
| **Manual trigger** | Dashboard only | `workflow_dispatch` ✅ |
| **AI enrichment possible?** | ❌ Too slow | ✅ Full pipeline runs fine |
| **Monthly cost** | $0 | $0 |

</div>

The 10-second Vercel timeout makes AI enrichment physically impossible on Vercel. GitHub Actions eliminates this constraint entirely — and costs nothing more.

---

## 🤖 AI Stack

<div align="center">

| Layer | Provider | Model | Purpose | Free Tier |
|:---|:---|:---|:---|:---:|
| **Text — Primary** | Google AI Studio | `gemini-2.0-flash` | Severity rating, technical analysis, IoC keywords, mitigation steps | 1,500 req/day |
| **Text — Fallback** | Groq | `llama-3.3-70b-versatile` | Auto-failover when Gemini hits rate limits | 14,400 req/day |
| **Image — Primary** | Hugging Face | `FLUX.1-schnell` | Unique AI-generated visual per article | ~1,000 img/day |
| **Image — Fallback** | Hugging Face | `stable-diffusion-xl-base-1.0` | If FLUX is temporarily unavailable | Free tier |

</div>

> **⚠️ 2026 API compatibility notes:**
> - `gemini-1.5-flash` was removed → use **`gemini-2.0-flash`**
> - `stable-diffusion-2-1` and `stable-diffusion-v1-5` return **`410 Gone`** (permanently deleted from HF)
> - Image generation must now use **`AsyncInferenceClient.text_to_image()`** from `huggingface_hub` SDK — the legacy `httpx POST` to `api-inference.huggingface.co` no longer works

---

## 📁 Project Structure

```
cyber-intel-v2/
│
├── .github/
│   └── workflows/
│       └── pipeline.yml              ← ⚡ THE cron engine (GitHub Actions)
│
├── pipeline/                         ← Runs inside GitHub Actions ONLY
│   ├── run.py                        ← Entry point: python pipeline/run.py
│   ├── fetchers/
│   │   ├── news.py                   ← 5 RSS feeds (concurrent asyncio)
│   │   ├── vulns.py                  ← NIST NVD CVE API v2.0
│   │   └── fraud_bugs.py             ← CISA, GitHub Advisories, CERT/CC
│   ├── enrichers/
│   │   ├── text_ai.py                ← Gemini 2.0-flash + Groq fallback
│   │   └── image_ai.py               ← FLUX.1-schnell via HuggingFace SDK
│   ├── storage/
│   │   └── blob.py                   ← Vercel Blob read/write helpers
│   └── utils/
│       └── helpers.py                ← Logging, SHA-256 IDs, timestamps
│
├── api/
│   └── index.py                      ← Vercel serverless (READ-ONLY, stdlib)
│                                        Uses BaseHTTPRequestHandler — NOT FastAPI
│
├── public/                           ← Static frontend served by Vercel
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── placeholders/                 ← SVG fallback images (4 categories)
│       ├── news.svg
│       ├── vulnerability.svg
│       ├── fraud.svg
│       └── bug.svg
│
├── .python-version                   ← Pins Python 3.12 for Vercel uv build
├── pyproject.toml                    ← Required by Vercel CLI 50+ (uv package manager)
├── requirements.txt                  ← Vercel API deps — stdlib only, intentionally empty
├── requirements-pipeline.txt        ← GitHub Actions deps (full AI stack)
├── vercel.json                       ← Routes + build config (NO cron section)
└── .env.example                      ← Template for local development
```

---

## 🚀 Deployment Guide

### Step 1 — Get Your API Keys (All Free)

<details>
<summary><b>🔐 Vercel Blob Token — <code>BLOB_READ_WRITE_TOKEN</code> &nbsp;(Required)</b></summary>
<br>

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Open your project → **Storage** tab → **Create Database** → **Blob**
3. After creation, click the **`.env.local`** tab
4. Copy the value: `vercel_blob_rw_...`

> **Free tier:** 500 MB storage · 1 GB bandwidth/month

</details>

<details>
<summary><b>🤖 Google Gemini Key — <code>GEMINI_API_KEY</code> &nbsp;(Primary AI)</b></summary>
<br>

1. Visit [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key** → select or create a project
3. Copy the key (starts with `AIzaSy...`)

> **Free tier:** 15 req/min · 1,500 req/day · model: `gemini-2.0-flash`

</details>

<details>
<summary><b>⚡ Groq Key — <code>GROQ_API_KEY</code> &nbsp;(Fallback — Strongly Recommended)</b></summary>
<br>

1. Sign up at [console.groq.com](https://console.groq.com)
2. **API Keys** → **Create API Key**
3. Copy (starts with `gsk_...`)

> **Free tier:** 30 req/min · 14,400 req/day · model: `llama-3.3-70b-versatile`

</details>

<details>
<summary><b>🎨 Hugging Face Token — <code>HF_API_TOKEN</code> &nbsp;(Image Generation)</b></summary>
<br>

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. **New token** → type **Read** → **Generate**
3. Copy (starts with `hf_...`)

> **Free tier:** ~1,000 image generations/day · model: `FLUX.1-schnell`

</details>

---

### Step 2 — Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from the project root
vercel
# → Link to existing project? N
# → Project name: cyberintel-hub
# → Override settings? N
```

Or import directly at [vercel.com/new](https://vercel.com/new) → Import GitHub repo.

Add **one** environment variable in **Vercel Dashboard → Project → Settings → Environment Variables:**

| Variable | Value | Environments |
|:---|:---|:---:|
| `BLOB_READ_WRITE_TOKEN` | `vercel_blob_rw_xxx...` | Production, Preview |

> Vercel only ever needs the Blob token. All AI keys live in GitHub Secrets — Vercel never calls any AI API.

---

### Step 3 — Set GitHub Secrets

**Repository → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Source | Required? |
|:---|:---|:---:|
| `BLOB_READ_WRITE_TOKEN` | Vercel Dashboard → Storage → Blob → `.env.local` | ✅ Yes |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | ✅ Yes |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com) | ⚡ Recommended |
| `HF_API_TOKEN` | [HuggingFace Settings](https://huggingface.co/settings/tokens) | 🎨 For images |

---

### Step 4 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: CyberIntel Hub v2.0 — AI pipeline on GitHub Actions"
git remote add origin https://github.com/mark-Aryan/cyber-intel-v2.git
git push -u origin main
```

GitHub Actions auto-detects `.github/workflows/pipeline.yml` on push and begins scheduling immediately.

---

### Step 5 — Test Everything

**Trigger the first run manually:**

1. Go to your repo → **Actions** tab
2. Click **🛡 CyberIntel Pipeline** in the left sidebar
3. **Run workflow** → **Run workflow** (enable `force_refresh` to re-enrich existing items)
4. Watch the live log — completes in **60–120 seconds**

**Verify the API is responding:**

```bash
# Health check
curl https://cyberintelv2.vercel.app/api/health
# {"status":"ok","counts":{"news":15,"vulnerability":10,"fraud":3,"bug":8},"total":36}

# Full data feed
curl https://cyberintelv2.vercel.app/api/data | python -m json.tool | head -60
```

Open [cyberintelv2.vercel.app](https://cyberintelv2.vercel.app) to see the live frontend.

---

## 💻 Local Development

```bash
# 1. Clone and create virtual environment
git clone https://github.com/mark-Aryan/cyber-intel-v2
cd cyber-intel-v2
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 2. Install pipeline dependencies
pip install -r requirements-pipeline.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env — add your BLOB_READ_WRITE_TOKEN, GEMINI_API_KEY, HF_API_TOKEN

# 4. Run the full pipeline locally
PYTHONPATH=. python pipeline/run.py

# 5. Serve the API locally (stdlib only — nothing extra to install)
python -c "
from http.server import HTTPServer
from api.index import handler
print('API → http://localhost:8000/api/health')
HTTPServer(('localhost', 8000), handler).serve_forever()
"

# 6. Serve the frontend
python -m http.server 3000 --directory public
# Open http://localhost:3000
```

> **Note on step 5:** The API now uses Python's `BaseHTTPRequestHandler` — no `uvicorn`, no `fastapi`, no extra installs needed. `uvicorn api.index:app` from v1 no longer applies.

---

## ⚙️ Configuration

### Change the Pipeline Schedule

Edit `.github/workflows/pipeline.yml`:

```yaml
on:
  schedule:
    - cron: '*/30 * * * *'      # Every 30 min  — current default
    # - cron: '0 * * * *'       # Every hour    — more conservative
    # - cron: '0 */2 * * *'     # Every 2 hours — safe for free tier
    # - cron: '0 6,12,18 * * *' # 3× daily      — minimum viable cadence
```

Commit and push — GitHub picks up the new schedule automatically.

### Tune Pipeline Limits

Edit `pipeline/run.py`:

```python
MAX_NEW_ITEMS_PER_RUN  = 15   # Cap per run (prevents timeout + rate-limit blowout)
MAX_AGE_DAYS           = 30   # Prune items older than N days from data.json
MAX_CONCURRENT_AI      = 3    # Asyncio semaphore for parallel AI enrichment calls
MAX_PER_CATEGORY       = 200  # Hard cap per category in data.json
```

### Add New RSS Feeds

Edit `pipeline/fetchers/news.py`:

```python
RSS_FEEDS = [
    ("The Hacker News",   "https://feeds.feedburner.com/TheHackersNews"),
    ("Bleeping Computer", "https://www.bleepingcomputer.com/feed/"),
    # Add yours here — no other changes required
    ("My Custom Feed",    "https://example.com/rss.xml"),
]
```

Commit → push → next pipeline run includes the new feed automatically.

---

## 📊 Monitoring & Maintenance

**GitHub Actions:** Actions tab → per-run execution times, live logs, downloadable `pipeline-log-{id}` artifact (90-day retention).

**Vercel Dashboard:** Functions tab → `/api/data` execution times. Analytics tab → request volume and CDN cache hit rate.

### Issues to Watch

| Symptom | Likely Cause | Fix |
|:---|:---|:---|
| `429` errors in pipeline log | Gemini rate limit hit | Lower `MAX_NEW_ITEMS_PER_RUN`, or ensure `GROQ_API_KEY` is set |
| `503` on first HF call, succeeds on retry | HuggingFace cold start | Expected — `tenacity` retry decorator handles this automatically |
| Save errors, oversized Blob | Approaching 500 MB free limit | Lower `MAX_AGE_DAYS` or `MAX_PER_CATEGORY` in `run.py` |
| Vuln fetcher errors | NIST NVD transient outage | Self-healing — next run picks up the gap |
| GitHub Actions billing warning | Free minutes nearly exhausted | Switch schedule to `0 */2 * * *` (every 2 hours) |

---

## 🔧 Troubleshooting

<details>
<summary><b>❌ Vercel returns 500 — <code>TypeError: issubclass() arg 1 must be a class</code></b></summary>
<br>

**Cause:** Vercel's `@vercel/python` runtime (2026) checks that your export is a `BaseHTTPRequestHandler` subclass. FastAPI + Mangum returns an ASGI callable — fails the `issubclass()` check.

**Fix:** Rewrite `api/index.py` as:
```python
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ...
```
Remove `fastapi`, `mangum`, and `httpx` from `requirements.txt`.

</details>

<details>
<summary><b>❌ Build fails — <code>No `project` table found in pyproject.toml</code></b></summary>
<br>

**Cause:** Vercel CLI 50+ uses `uv` as the Python build backend. `uv lock` requires a valid `[project]` table.

**Fix:** Add to the repo root:

**`pyproject.toml`**
```toml
[project]
name = "cyberintel-hub"
version = "2.0.0"
requires-python = ">=3.12"
dependencies = []
```

**`.python-version`**
```
3.12
```

</details>

<details>
<summary><b>❌ Gemini error — <code>404 models/gemini-1.5-flash is not found</code></b></summary>
<br>

**Cause:** `gemini-1.5-flash` was renamed in the v1beta API in early 2026.

**Fix** in `pipeline/enrichers/text_ai.py`:
```python
GEMINI_MODEL = "gemini-2.0-flash"   # was: "gemini-1.5-flash"
```

</details>

<details>
<summary><b>❌ HuggingFace image generation returns <code>410 Gone</code></b></summary>
<br>

**Cause:** `stable-diffusion-2-1` and `stable-diffusion-v1-5` were permanently deleted. The old `httpx POST` to `api-inference.huggingface.co/models/{model}` is dead.

**Fix** in `pipeline/enrichers/image_ai.py`:
```python
from huggingface_hub import AsyncInferenceClient
import io

async def generate_image(prompt: str, token: str) -> bytes:
    client = AsyncInferenceClient(api_key=token)
    pil_image = await client.text_to_image(
        prompt=prompt,
        model="black-forest-labs/FLUX.1-schnell",
    )
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()
```

Add to `requirements-pipeline.txt`:
```
huggingface_hub>=0.28.0
Pillow>=10.0.0
```

</details>

<details>
<summary><b>❌ All images show as broken / only SVG placeholders</b></summary>
<br>

**Cause:** `public/placeholders/` directory doesn't exist — all items fall back to `/placeholders/news.svg`, which 404s.

**Fix:** Create `public/placeholders/` and add: `news.svg`, `vulnerability.svg`, `fraud.svg`, `bug.svg`.

</details>

<details>
<summary><b>⚠️ Warning — <code>Illegal header value</code> for BLOB_READ_WRITE_TOKEN</b></summary>
<br>

Invisible trailing whitespace pasted from the GitHub Secrets UI. Already handled in `blob.py` with `.strip()`. If it persists, re-copy the token from Vercel Dashboard → Storage → Blob → `.env.local` and paste fresh.

</details>

---

## 💰 Free Tier Usage

<div align="center">

| Service | Free Allowance | CyberIntel Hub Usage | Status |
|:---|:---:|:---:|:---:|
| **GitHub Actions** | 2,000 min/month | ~1,440 min (48 runs/day × ~1 min) | ✅ Safe |
| **Vercel Hobby** | Unlimited static + 100 GB BW | Minimal reads only | ✅ Safe |
| **Vercel Blob** | 500 MB · 1 GB BW/month | ~30 MB/month | ✅ Safe |
| **Gemini 2.0-flash** | 1,500 req/day | ~720 req/day max | ✅ Safe |
| **Groq Llama-3.3** | 14,400 req/day | Fallback only | ✅ Safe |
| **Hugging Face** | ~1,000 img/day | ~300 img/day max | ✅ Safe |
| **NIST NVD API** | 5 req/30s (no key needed) | 1 req/30 min | ✅ Safe |

### 💵 Total Monthly Cost: `$0.00`

</div>

---

## 🤝 Contributing

Contributions are welcome. To add a new intelligence source:

1. Fork the repository
2. Create a new fetcher in `pipeline/fetchers/`
3. Register it in `pipeline/run.py` inside the `asyncio.gather()` call
4. Open a pull request with a description of the source and its feed format

For bugs or feature requests, open a [GitHub Issue](https://github.com/mark-Aryan/cyber-intel-v2/issues).

---

## 👤 Author

<div align="center">

<img src="https://img.shields.io/badge/Aryan%20Kumar%20Upadhyay-codeXploit-00ff88?style=for-the-badge&logo=hackthebox&logoColor=black"/>

**Cybersecurity Analyst · Ethical Hacker · Penetration Tester · Full-Stack Developer**

🇮🇳 India &nbsp;·&nbsp; 3+ years security experience &nbsp;·&nbsp; 4+ years freelancing

<br>

[![Portfolio](https://img.shields.io/badge/Portfolio-codexploit.in-00e5ff?style=flat-square)](https://codexploit.in/)
&nbsp;
[![GitHub](https://img.shields.io/badge/GitHub-mark--Aryan-181717?style=flat-square&logo=github)](https://github.com/mark-Aryan)
&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-aryan--kumar--upadhyay-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/aryan-kumar-upadhyay)
&nbsp;
[![Fiverr](https://img.shields.io/badge/Hire_Me-Fiverr%3A_mark__aryan-1DBF73?style=flat-square&logo=fiverr&logoColor=white)](https://www.fiverr.com/mark_aryan)
&nbsp;
[![Twitter](https://img.shields.io/badge/Twitter-@aryankrupadhyay-1DA1F2?style=flat-square&logo=twitter)](https://twitter.com/aryankrupadhyay)

</div>

---

## 📄 License

```
MIT License — Copyright (c) 2026 Aryan Kumar Upadhyay (codeXploit)

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software.
```

---

<!-- ═══════════════════════  FOOTER BANNER  ═══════════════════════ -->
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&height=130&color=0:050509,50:0a1628,100:001a0a&section=footer&text=codeXploit%20%C2%B7%20Aryan%20Kumar%20Upadhyay&fontSize=16&fontColor=00ff88&animation=fadeIn" width="100%"/>

**⭐ Star this repo if CyberIntel Hub saved you time or inspired your own build**

*Made with ❤️ by [Aryan Kumar Upadhyay (codeXploit)](https://codexploit.in/) — Cybersecurity Analyst & Ethical Hacker · India*

</div>
