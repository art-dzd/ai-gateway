# AI Gateway (LLM/AI Integrations Service)

Сервис‑шлюз для интеграции с внешними AI API (LLM/embeddings/image generation): единый вход, очереди, ретраи, лимиты, аудит, учёт стоимости, вебхуки.

Этот репозиторий задуман как **публичный**, поэтому:
- секреты не коммитим (только `.env.example`);
- по умолчанию не храним “сырые” промпты/ответы (только метаданные и redacted payload);
- есть `MockProvider`, чтобы всё запускалось локально без ключей и денег.

## Фичи (MVP)
- `POST /v1/responses` — основной sync proxy (OpenAI‑compatible Responses API).
- `POST /v1/chat/completions` — back-compat sync proxy (без стрима).
- `GET /v1/models` — discovery (для openai‑compatible проксируем `/v1/models`, кэшируем в Redis).
- `POST /v1/jobs` + `GET /v1/jobs/{id}` — async jobs (Celery+Redis) + доставка результата на webhook.
- API‑ключи клиентов (`X-API-Key`), rate limit и бюджеты.
- PostgreSQL для состояния и аудита, Redis для очереди и лимитов.
- Метрики Prometheus `/metrics`, healthchecks `/healthz` и `/readyz`.
- Мини‑дашборд `/dashboard` (Basic Auth).

## Быстрый старт (локально, через Docker)
1) Поднять инфраструктуру:
```bash
docker compose up -d --build
```

2) Применить миграции:
```bash
docker compose run --rm api alembic upgrade head
```

3) Создать клиентский ключ (показывается один раз):
```bash
docker compose run --rm api ai-gateway create-key --name local
```
Формат нового ключа: `agw_<id>.<secret>` (старые ключи без точки тоже принимаются, но медленнее).

4) Проверка:
- `GET http://localhost:8010/healthz`
- `GET http://localhost:8010/readyz`
- `GET http://localhost:8010/dashboard` (Basic Auth из `.env`)

Пример `POST /v1/responses` (mock):
```bash
curl -s http://localhost:8010/v1/responses \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ВАШ_КЛЮЧ>" \
  -d '{"model":"mock-1","input":"Привет, расскажи анекдот"}'
```

Пример async job:
```bash
curl -s http://localhost:8010/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ВАШ_КЛЮЧ>" \
  -d '{"kind":"responses","payload":{"model":"mock-1","input":"Hello from job"}}'
```

## OpenAI-compatible провайдер
В `.env`:
- `DEFAULT_PROVIDER=openai`
- `OPENAI_BASE_URL` (можно с `/v1` или без)
- `OPENAI_API_KEY`
- опционально (полезно для OpenRouter): `OPENAI_HTTP_REFERER`, `OPENAI_TITLE`

Для `/v1/responses` шлюз по умолчанию подставляет `store=false`, если поле не задано (безопасный дефолт).
