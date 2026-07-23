# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    GROQ_API_KEY: str 
    GROQ_MODEL: str ='openai/gpt-oss-120b'
    GEMINI_ANSWER_MODEL: str = "gemini-2.5-flash" 
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # ── App Settings ──────────────────────
    APP_NAME: str = "Pakistan Route AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ── PostgreSQL / pgAdmin ──────────────
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "yourpassword"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pakistan_route_ai"


    SERPAPI_API_KEY: str
    GOOGLE_CSE_API_KEY: str
    GOOGLE_CSE_CX: str
    # ── Computed DB URL ───────────────────
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis ─────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL_SECONDS: int = 18  # 30 minutes

    # ── OpenAI ────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"          # Cheap for extraction
    OPENAI_ANSWER_MODEL: str = "gpt-4o"        # Better for final answers

    # ── Weather API ───────────────────────
    OPENWEATHER_API_KEY: str

    # ── Qdrant Vector DB ─────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "pakistan_routes"

    # ── Scraping Settings ─────────────────
    SCRAPE_DELAY_SECONDS: float = 2.5
    MAX_CONCURRENT_SCRAPERS: int = 3
    SCRAPE_TIMEOUT_SECONDS: int = 30

    # ── Pakistan News Sources ─────────────
    NEWS_SOURCES: List[str] = [
        "https://www.dawn.com",
        "https://www.geo.tv",
        "https://arynews.tv",
        "https://nhmp.gov.pk",
        "https://www.pmd.gov.pk",
        "https://tribune.com.pk",
    ]

    #facebook app 
    GRAPH_API_VERSION:str
    FB_PAGE_ID:str
    FB_PAGE_ACCESS_TOKEN:str

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()