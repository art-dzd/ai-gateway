"""SQLAlchemy модели (Postgres)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Текущее время в UTC (timezone-aware)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей."""


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    key_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_budget_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_budget_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    requests: Mapped[list["RequestLog"]] = relationship(back_populates="api_key")
    jobs: Mapped[list["Job"]] = relationship(back_populates="api_key")


class RequestLog(Base):
    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), nullable=False)

    kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # responses | chat.completions | models
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(20), nullable=False)  # succeeded | failed
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    request_payload_redacted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_payload_redacted: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    api_key: Mapped[ApiKey] = relationship(back_populates="requests")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "api_key_id",
            "idempotency_key",
            name="uq_jobs_api_key_id_idempotency_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), nullable=False)

    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # responses | chat.completions
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")

    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    payload_redacted: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    result_redacted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    api_key: Mapped[ApiKey] = relationship(back_populates="jobs")
    attempts: Mapped[list["JobAttempt"]] = relationship(back_populates="job")
    webhook_deliveries: Mapped[list["WebhookDelivery"]] = relationship(back_populates="job")


class JobAttempt(Base):
    __tablename__ = "job_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # succeeded | failed
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    job: Mapped[Job] = relationship(back_populates="attempts")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    job: Mapped[Job] = relationship(back_populates="webhook_deliveries")
