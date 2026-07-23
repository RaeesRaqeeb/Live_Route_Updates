# 🇵🇰 Pakistan Route AI

AI-powered travel intelligence system for Pakistan get real-time route news,
weather, road conditions, and safety alerts for any origin → destination.

## 🧠 How It Works

The system is split into two decoupled pipelines: a **scheduled background pipeline**
that keeps route data fresh, and a **real-time request pipeline** that serves users
from the database instead of scraping on every request.

### Scheduled pipeline (runs every ~45 min, independent of user traffic)

1. Iterates over all active routes in the database (seeded manually + auto-discovered
   from user searches)
2. For each route, gathers raw source data from multiple channels:
   - **NHMP Travel Advisory API** (direct)
   - **SerpAPI** → Google/Facebook search (news sites, public FB posts about road
     conditions)
   - **Crawl4AI** → direct scrape of public Facebook pages via `mbasic.facebook.com`
   - **Facebook Graph API** → posts from our own official Page (used specifically
     for Gilgit-Baltistan / Karakoram Highway routes, where no dedicated
     road-authority API exists)
3. Each raw item is **hashed (SHA-256)**; if content is unchanged since the last run,
   it's skipped — no redundant LLM calls
4. New/changed content is passed to an **LLM extractor (Groq + Llama, structured
   output)**, which converts raw text into structured alerts: headline, issue type,
   severity, affected route, summary
5. Structured alerts are stored in PostgreSQL (`scrape_results`), tagged with source
   and timestamp, with an expiry window so stale alerts auto-deactivate

### Real-time request pipeline (per user search)

1. User enters **origin** and **destination** (e.g., Lahore → Islamabad), or a free-text
   query that's parsed into origin/destination
2. System checks Redis cache first (10 min TTL) — returns immediately on hit
3. On cache miss, fetches **live weather** via OpenWeatherMap for both cities
4. Looks up (or auto-registers) the route, then queries PostgreSQL for recent,
   active alerts (default freshness window: 3 hours)
   - If fresh DB data exists → used directly, **no scraping, no extraction LLM
     call** on the request path
   - If no data yet for a brand-new route → one-time live scrape + extraction as a
     fallback, so the first search for a new route still gets an answer while the
     scheduled job takes over for subsequent requests
5. A **RAG-style synthesis step (Gemini)** combines the structured alerts + weather
   into a short natural-language travel briefing and an overall alert level
   (safe / caution / danger)
6. Response is cached in Redis, and the query is logged to PostgreSQL
   (`user_queries`) in the background for analytics

This DB-first design means scraping and LLM extraction happen on a predictable
schedule (protecting API quotas and avoiding source-site blocking), while user
requests stay fast because they read from the database instead of triggering live
scrapes.

## 🛠️ Tech Stack

| Layer               | Technology                                      |
|---------------------|--------------------------------------------------|
| Package Manager      | UV                                               |
| Web Framework        | FastAPI                                          |
| Database             | PostgreSQL 16                                    |
| DB Admin             | pgAdmin 4                                        |
| ORM                  | SQLAlchemy 2.0 (async)                           |
| Migrations           | Alembic                                          |
| Scraping             | Crawl4AI + Playwright, SerpAPI (Google/FB search)|
| Social Data          | Facebook Graph API (own Page, GB/KKH routes)     |
| Extraction LLM       | Groq (Llama, structured outputs)                 |
| Synthesis / RAG LLM  | Google Gemini                                    |
| Weather              | OpenWeatherMap API                               |
| Scheduling           | APScheduler (background scrape job)              |
| Cache                | Redis (+ PostgreSQL as persistent fallback cache) |
| Containers           | Docker Compose                                   |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- UV installed

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourname/pakistan-route-ai
cd pakistan-route-ai

# 2. Install dependencies
uv sync

# 3. Setup environment
cp .env.example .env
# Edit .env with your API keys (see below)

# 4. Start services (PostgreSQL, pgAdmin, Redis)
docker-compose up -d

# 5. Run database migrations
uv run alembic upgrade head

# 6. Install Playwright browser
uv run playwright install chromium

# 7. Seed initial routes (optional but recommended)
uv run python scripts/seed_routes.py

# 8. Start the API server
uv run uvicorn app.main:app --reload --port 8000
```

The scheduled scraper starts automatically on app startup (via APScheduler) and
runs every ~45 minutes. To test it immediately without waiting:

```bash
uv run python -c "import asyncio; from app.jobs.scheduled_scraper import run_scheduled_scrape; asyncio.run(run_scheduled_scrape())"
```

### Required environment variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Weather
OPENWEATHER_API_KEY=...

# Extraction LLM (Groq)
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile

# Synthesis LLM (Gemini)
GEMINI_API_KEY=...
GEMINI_ANSWER_MODEL=...

# SerpAPI (Google/Facebook search fallback)
SERPAPI_API_KEY=...

# Facebook Graph API (own Page — GB/KKH route updates)
FB_PAGE_ID=...
FB_PAGE_ACCESS_TOKEN=...   # long-lived Page token
GRAPH_API_VERSION=v19.0

# Redis
REDIS_URL=redis://localhost:6379
```

## 🔗 Access Points

- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- pgAdmin: http://localhost:5050
- Health Check: http://localhost:8000/health

## 📡 Example API Call

```bash
curl -X POST "http://localhost:8000/api/v1/route/info" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Lahore",
    "destination": "Islamabad",
    "query_type": "all"
  }'
```

Natural language input is also supported:

```bash
curl -X POST "http://localhost:8000/api/v1/route/info" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Is it safe to drive from Islamabad to Skardu right now?"
  }'
```

## 🗄️ Data Freshness & Source Strategy

- **Most routes**: NHMP API, news sites, and SerpAPI-based search are scraped on
  the scheduled cycle and considered fresh for up to 3 hours before a request falls
  back to a live re-scrape.
- **Gilgit-Baltistan / KKH routes**: additionally pull from our own Facebook Page
  via the Graph API, since no dedicated road-authority API exists for this region.
  This is treated as a higher-trust source and is actively being supplemented with
  outreach to established local pages (e.g., KKH Updates, GBDMA) for a more
  reliable long-term feed.
- Every alert stored includes its `source_name`, `source_url`, and a
  `content_hash` used to avoid redundant LLM extraction calls when source content
  hasn't changed between scrape cycles.

## 🧪 Run Tests

```bash
uv run pytest tests/ -v
```
