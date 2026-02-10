"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rpm_limit", sa.Integer(), nullable=True),
        sa.Column("daily_budget_rub", sa.Numeric(12, 2), nullable=True),
        sa.Column("monthly_budget_rub", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "requests",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("api_key_id", sa.Uuid(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_rub", sa.Numeric(12, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_payload_redacted", sa.JSON(), nullable=True),
        sa.Column("response_payload_redacted", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_requests_api_key_id_created_at", "requests", ["api_key_id", "created_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("api_key_id", sa.Uuid(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("payload_redacted", sa.JSON(), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("webhook_secret", sa.Text(), nullable=True),
        sa.Column("webhook_headers", sa.JSON(), nullable=True),
        sa.Column("result_redacted", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("api_key_id", "idempotency_key", name="uq_jobs_api_key_id_idempotency_key"),
    )
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])

    op.create_table(
        "job_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_webhook_deliveries_job_id_created_at", "webhook_deliveries", ["job_id", "created_at"])


def downgrade():
    op.drop_index("ix_webhook_deliveries_job_id_created_at", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_table("job_attempts")
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_requests_api_key_id_created_at", table_name="requests")
    op.drop_table("requests")
    op.drop_table("api_keys")

