# app/core/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from app.core.config import settings
from sqlalchemy import text

# ── Async Engine ──────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # Log SQL in debug mode
    pool_size=5,                   # Connections to keep open
    max_overflow=10,               # Extra connections when pool is full
    pool_timeout=30,               # Seconds to wait for connection
    pool_recycle=1800,             # Recycle connections every 30 min
    pool_pre_ping=True,            # Test connection health before use
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Prevent lazy loading issues after commit
    autocommit=False,
    autoflush=False,
)


# ── Base Model Class ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── Auto-Create Database if Missing ──────────────────────────────────────────
async def create_database_if_not_exists():
    """
    Connects to the default 'postgres' DB first,
    then creates our app database if it doesn't exist.
    This runs BEFORE the main engine tries to connect.
    """
    # Build URL pointing to default 'postgres' database
    default_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/postgres"   # ← connect to default DB
    )

    default_engine = create_async_engine(
        default_url,
        isolation_level="AUTOCOMMIT",   # Required for CREATE DATABASE
        echo=False,
    )

    try:
        async with default_engine.connect() as conn:
            # Check if database already exists
            result = await conn.execute(
                text(
                    "SELECT 1 FROM pg_catalog.pg_database "
                    "WHERE datname = :dbname"
                ),
                {"dbname": settings.POSTGRES_DB},
            )
            exists = result.fetchone()

            if not exists:
                # Create it!
                await conn.execute(
                    text(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
                )
                print(f"✅ Database '{settings.POSTGRES_DB}' created successfully!")
            else:
                print(f"✅ Database '{settings.POSTGRES_DB}' already exists.")

    except Exception as e:
        print(f"❌ Could not create database: {e}")
        raise
    finally:
        await default_engine.dispose()


# ── Dependency: DB Session per Request ───────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()