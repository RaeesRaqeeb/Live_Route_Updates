# 🇵🇰 Pakistan Route AI

AI-powered travel intelligence system for Pakistan — get real-time route news,
weather, road conditions, and safety alerts for any origin → destination.

## 🧠 How It Works

1. User enters **origin** and **destination** (e.g., Lahore → Islamabad)
2. System fetches **live weather** via OpenWeatherMap API
3. **Crawl4AI** scrapes Pakistani news sites (Dawn, Geo, ARY, NHMP)
4. **LLM** extracts structured route alerts from raw scraped text
5. **RAG pipeline** retrieves most relevant info and generates a final answer
6. Results are **cached in Redis** for 30 minutes to avoid redundant scraping

## 🛠️ Tech Stack

| Layer          | Technology          |
|----------------|---------------------|
| Package Manager| UV                  |
| Web Framework  | FastAPI             |
| Database       | PostgreSQL 16       |
| DB Admin       | pgAdmin 4           |
| ORM            | SQLAlchemy 2.0      |
| Migrations     | Alembic             |
| Scraping       | Crawl4AI + Playwright|
| LLM            | OpenAI GPT-4o-mini  |
| Vector Store   | Qdrant              |
| Cache          | Redis               |
| Containers     | Docker Compose      |

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
# Edit .env with your API keys

# 4. Start services (PostgreSQL, pgAdmin, Redis)
docker-compose up -d

# 5. Run database migrations
uv run alembic upgrade head

# 6. Install Playwright browser
uv run playwright install chromium

# 7. Start the API server
uv run uvicorn app.main:app --reload --port 8000

🔗 Access Points

    API Docs (Swagger): http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc
    pgAdmin: http://localhost:5050
    Health Check: http://localhost:8000/health


📡 Example API Call

Bash

curl -X POST "http://localhost:8000/api/v1/route/info" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Lahore",
    "destination": "Islamabad",
    "query_type": "all"
  }'

🧪 Run Tests

Bash

uv run pytest tests/ -v