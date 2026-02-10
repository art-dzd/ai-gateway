FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=60

COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src /app/src

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U setuptools wheel --retries 10 --timeout 60 && \
    pip install --no-cache-dir -e . --no-build-isolation --retries 10 --timeout 60

EXPOSE 8000

CMD ["uvicorn", "ai_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
