"""create initial tables

Revision ID: 001
Revises:
Create Date: 2026-july-14 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── routes ────────────────────────────────────────────────────────────────
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("origin_city", sa.String(100), nullable=False),
        sa.Column("destination_city", sa.String(100), nullable=False),
        sa.Column("route_name", sa.String(200), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("route_type", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routes_origin_city", "routes", ["origin_city"])
    op.create_index("ix_routes_destination_city", "routes", ["destination_city"])

    # ── scrape_results ────────────────────────────────────────────────────────
    op.create_table(
        "scrape_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("routes.id"), nullable=True),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("headline", sa.String(500), nullable=True),
        sa.Column("route_affected", sa.String(200), nullable=True),
        sa.Column("issue_type", sa.String(50), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── user_queries ──────────────────────────────────────────────────────────
    op.create_table(
        "user_queries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("origin_input", sa.String(200), nullable=True),
        sa.Column("destination_input", sa.String(200), nullable=True),
        sa.Column("normalized_origin", sa.String(100), nullable=True),
        sa.Column("normalized_dest", sa.String(100), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), default=False),
        sa.Column("sources_used", sa.Text(), nullable=True),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_queries_session_id", "user_queries", ["session_id"])

    # ── query_cache ───────────────────────────────────────────────────────────
    op.create_table(
        "query_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_key", sa.String(255), unique=True, nullable=False),
        sa.Column("origin", sa.String(100), nullable=True),
        sa.Column("destination", sa.String(100), nullable=True),
        sa.Column("cached_response", sa.Text(), nullable=True),
        sa.Column("hit_count", sa.Integer(), default=0),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_cache_cache_key", "query_cache", ["cache_key"])


def downgrade() -> None:
    op.drop_table("query_cache")
    op.drop_table("user_queries")
    op.drop_table("scrape_results")
    op.drop_table("routes")