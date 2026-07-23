# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base,create_database_if_not_exists
from app.routers import route_info, weather, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── Startup ──────────────────────────
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await create_database_if_not_exists()  
    # Create all DB tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    start_scheduler()
    print("✅ Database tables ready")
    print("✅ Crawl4AI scraper ready")

    yield  # App runs here

    # ── Shutdown ─────────────────────────
    await engine.dispose()
    print("👋 Shutting down, connections closed.")


# ── App Instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Pakistan route news, weather & road condition API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# app/main.py 
from app.core.scheduler import start_scheduler



# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(route_info.router, prefix=settings.API_PREFIX, tags=["Routes"])
app.include_router(weather.router, prefix=settings.API_PREFIX, tags=["Weather"])