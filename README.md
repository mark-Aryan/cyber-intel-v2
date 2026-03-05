# CyberIntel Hub v2.0 🛡

> Real-time AI-powered cybersecurity intelligence.  
> **GitHub Actions** runs the pipeline · **Vercel** hosts the frontend · 100% free.

---

## Why GitHub Actions instead of Vercel Cron?

| | Vercel Hobby Cron | GitHub Actions |
|---|---|---|
| **Schedule frequency** | Daily only | Any interval (we use 30 min) |
| **Execution timeout** | 10 seconds | 6 hours |
| **Free minutes** | N/A | 2,000 min/month |
| **Cost** | $0 (daily only) | $0 |
| **Manual trigger** | Via dashboard only | Yes — `workflow_dispatch` |

GitHub Actions is strictly better for a solo developer on a free plan.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  GitHub Actions (runs every 30 min)                          │
│                                                              │
│  python pipeline/run.py                                      │
│    │                                                         │
│    ├─ fetch_news()          ← 5 RSS feeds                    │
│    ├─ fetch_vulnerabilities()  ← NIST NVD CVE API            │
│    ├─ fetch_fraud()         ← CISA / FTC / IC3               │
│    └─ fetch_bugs()          ← GitHub Advisories / CERT       │
│         │                                                    │
│         ▼ (new items only — SHA-256 dedup)                   │
│    ├─ enrich_item_text()    ← Gemini 1.5 Flash / Groq        │
│    ├─ generate_and_upload_image()  ← HuggingFace SD 2.1      │
│    └─ save_data_json()      ─────────────────────────────┐   │
└──────────────────────────────────────────────────────────│───┘
                                                           │
                                              Vercel Blob (CDN)
                                                   data.json
                                                   images/
                                                           │
┌──────────────────────────────────────────────────────────│───┐
│  Vercel (always on)                                       │   │
│                                                           │   │
│  GET /api/data  ──reads──────────────────────────────────┘   │
│  GET /api/health                                             │
│                                                              │
│  /public/index.html  ← polls /api/data every 60s            │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
cyberintel/
│
├── .github/
│   └── workflows/
│       └── pipeline.yml         ← THE cron engine (GitHub Actions)
│
├── pipeline/                    ← Runs in GitHub Actions
│   ├── run.py                   ← Entry point (python pipeline/run.py)
│   ├── fetchers/
│   │   ├── news.py              ← 5 RSS feeds
│   │   ├── vulns.py             ← NIST NVD API
│   │   └── fraud_bugs.py        ← CISA, GitHub Advisories, etc.
│   ├── enrichers/
│   │   ├── text_ai.py           ← Gemini + Groq
│   │   └── image_ai.py          ← Hugging Face Stable Diffusion
│   ├── storage/
│   │   └── blob.py              ← Vercel Blob read/write
│   └── utils/
│       └── helpers.py
│
├── api/
│   └── index.py                 ← Vercel serverless (READ ONLY)
│
├── public/                      ← Static frontend
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── placeholders/            ← SVG fallback images
│
├── requirements.txt             ← Vercel deps (minimal: fastapi, httpx)
├── requirements-pipeline.txt   ← GitHub Actions deps (full AI stack)
├── vercel.json                  ← Routing config (NO cron jobs)
└── .env.example
```

---

## Step 1 — Get Your API Keys (All Free)

### 1a. Vercel Blob Token (`BLOB_READ_WRITE_TOKEN`)
1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Open your project → **Storage** tab → **Create Database** → **Blob**
3. After creation, click the **.env.local** tab
4. Copy `BLOB_READ_WRITE_TOKEN=vercel_blob_rw_...`

**Free tier:** 500 MB storage, 1 GB bandwidth/month

---

### 1b. Google Gemini Key (`GEMINI_API_KEY`)
1. Visit [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key** → select or create a project
3. Copy the key (starts with `AIzaSy...`)

**Free tier:** 15 req/min, 1M tokens/min, 1,500 req/day

---

### 1c. Groq Key (`GROQ_API_KEY`) — *Fallback, recommended*
1. Sign up at [console.groq.com](https://console.groq.com)
2. **API Keys** → **Create API Key**
3. Copy (starts with `gsk_...`)

**Free tier:** 30 req/min, 14,400 req/day

---

### 1d. Hugging Face Token (`HF_API_TOKEN`) — *Optional for images*
1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. **New token** → name it → type **Read** → **Generate**
3. Copy (starts with `hf_...`)

**Free tier:** ~1,000 image generations/day

---

## Step 2 — Deploy to Vercel

```bash
# Install Vercel CLI if you haven't
npm install -g vercel

# From the project root
vercel

# Follow prompts:
#   Link to existing project? N
#   Project name: cyberintel-hub
#   Override settings? N
```

Or use the dashboard: [vercel.com/new](https://vercel.com/new) → Import GitHub repo.

**Add environment variables** in Vercel Dashboard → Project → Settings → Environment Variables:

| Name | Value | Environments |
|---|---|---|
| `BLOB_READ_WRITE_TOKEN` | `vercel_blob_rw_xxx...` | Production, Preview |

> Note: Vercel only needs `BLOB_READ_WRITE_TOKEN` — the AI keys are only needed by GitHub Actions.

---

## Step 3 — Set GitHub Secrets

In your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

Add all four secrets:

| Secret Name | Where to get it |
|---|---|
| `BLOB_READ_WRITE_TOKEN` | Vercel Dashboard → Storage → Blob → .env.local |
| `GEMINI_API_KEY` | Google AI Studio |
| `GROQ_API_KEY` | Groq Console |
| `HF_API_TOKEN` | Hugging Face Settings |

---

## Step 4 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: CyberIntel Hub v2.0 — GitHub Actions pipeline"
git remote add origin https://github.com/yourusername/cyberintel-hub.git
git push -u origin main
```

GitHub Actions will:
- Automatically detect `.github/workflows/pipeline.yml`
- Schedule the pipeline to run every 30 minutes
- Show each run in the **Actions** tab of your repo

---

## Step 5 — Test Everything

### Trigger the pipeline manually (first run):
1. Go to your repo → **Actions** tab
2. Click **🛡 CyberIntel Pipeline** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch the live log — should complete in 60–120 seconds

### Verify data was stored:
```bash
curl https://your-project.vercel.app/api/health
# Expected: {"status":"ok","counts":{"news":5,"vulnerability":3,...}}

curl https://your-project.vercel.app/api/data | python -m json.tool | head -40
```

### View the frontend:
Open `https://your-project.vercel.app` in your browser.

---

## Monitoring & Maintenance

### GitHub Actions Dashboard
- **Actions tab** → See every run, execution time, pass/fail
- Click any run → View step-by-step logs
- Failed runs → Download the `pipeline-log-*.txt` artifact for full details

### Vercel Dashboard
- **Functions** tab → Execution times for `/api/data`
- **Analytics** tab → Request counts, latency

### Key things to watch

| Issue | Symptom | Fix |
|---|---|---|
| Gemini rate limit | `429` errors in pipeline log | Reduce `MAX_NEW_ITEMS_PER_RUN` or add `GROQ_API_KEY` |
| HF cold start | `503` errors, slow runs | Normal — the 2nd retry succeeds |
| Blob full (>500MB) | Save errors | Reduce `MAX_AGE_DAYS` or `MAX_PER_CATEGORY` |
| NVD API down | Vuln fetcher errors | Transient — next run picks up |
| Free tier exhausted | Actions → "Billing" warning | Reduce schedule to `0 */2 * * *` (every 2h) |

---

## Changing the Schedule

Edit `.github/workflows/pipeline.yml`:

```yaml
schedule:
  - cron: '*/30 * * * *'   # Every 30 min (current)
  - cron: '0 * * * *'      # Every hour (more conservative)
  - cron: '0 */2 * * *'    # Every 2 hours (very safe for free tier)
  - cron: '0 6,12,18 * * *' # 3× daily (minimum updates)
```

After editing, commit and push — GitHub picks up the new schedule automatically.

---

## Adding New RSS Feeds

Edit `pipeline/fetchers/news.py`:
```python
RSS_FEEDS = [
    ...
    ("My New Feed", "https://example.com/rss.xml"),
]
```
Commit → push → done. The next pipeline run will include your new feed.

---

## Local Development

```bash
# 1. Clone and set up
git clone https://github.com/yourusername/cyberintel-hub
cd cyberintel-hub
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt

# 2. Configure secrets
cp .env.example .env
# Edit .env with your actual keys

# 3. Run the pipeline locally
PYTHONPATH=. python pipeline/run.py

# 4. Run the Vercel API locally
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
# Visit http://localhost:8000/api/health

# 5. Serve the frontend
python -m http.server 3000 --directory public
# Visit http://localhost:3000
```

---

## Free Tier Usage Summary

| Service | Free Allowance | Our Usage | Status |
|---|---|---|---|
| GitHub Actions | 2,000 min/month | ~1,440 min/month (30-min schedule, ~1 min/run) | ✅ Safe |
| Vercel Hobby | Unlimited static + functions | Minimal reads only | ✅ Safe |
| Vercel Blob | 500 MB / 1 GB BW | ~30 MB/month | ✅ Safe |
| Gemini 1.5 Flash | 1,500 req/day | ~720 req/day max | ✅ Safe |
| Groq Llama-3 | 14,400 req/day | Fallback only | ✅ Safe |
| Hugging Face | ~1,000 img/day | ~300 img/day max | ✅ Safe |
| NIST NVD | 5 req/30s | 1 req/30 min | ✅ Safe |

**Total monthly cost: $0.00** ✅
