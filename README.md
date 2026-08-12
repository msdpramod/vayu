# Vayu

Vayu is a Jarvis-style personal assistant backend MVP focused on safe, explicit command execution.

## What works now

- FastAPI backend
- `GET /`, `GET /health`, `GET /skills`
- `POST /command` orchestration API
- Safe allow-listed skills: greeting, service status, and UTC time
- Intent routing for skills, memory, and AI reasoning fallback
- Durable SQLite-backed memory with `remember ...`, `what do you remember`, and `GET /memory`
- Pluggable AI provider boundary with an offline-safe fallback
- Explicit blocking for destructive, financial, credential, and security-sensitive commands
- Confirmation boundary for sensitive system actions
- Durable command audit trail at `GET /audit`
- Secret redaction for common password, token, API-key, and secret labels before audit persistence
- Durable request idempotency for `POST /command` using optional caller-supplied `request_id`
- Request-ID collision protection: the same ID cannot be reused for a different command or confirmation state
- Automated API, safety, memory, persistence, routing, audit, and idempotency tests
- Docker image + Docker Compose
- GitHub Actions CI configuration

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- http://localhost:8000/
- http://localhost:8000/docs
- http://localhost:8000/health
- http://localhost:8000/memory
- http://localhost:8000/audit

Try:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"remember my favorite editor is IntelliJ","request_id":"req-memory-0001"}'

curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"what do you remember"}'
```

If a client retries the first request with the same `request_id`, Vayu returns the cached response without executing the command or writing a second audit event. Reusing that ID with a different command or a different `confirmed` value returns HTTP `409 Conflict`.

## Runtime data

By default Vayu stores durable state in `data/vayu.db`. Override it with `VAYU_DB_PATH`.

Runtime databases and `.env` files are ignored by Git. Do not commit credentials or provider keys.

## Docker

```bash
docker compose up --build
```

## Architecture direction

Next milestones:

1. Real external LLM provider integration with timeouts and error isolation
2. Voice input/output (STT/TTS)
3. Richer explicit skill registry and scoped permissions
4. Desktop agent with narrowly scoped executors
5. Browser control
6. Calendar/email integrations
7. Smart-home integrations
8. Long-term semantic memory and retrieval
9. Observability/metrics and structured tracing
10. Mobile/web UI

Vayu must never execute arbitrary shell commands directly. Every action capability should be an explicit skill with scoped permissions, confirmation rules, idempotency where side effects are possible, and an auditable outcome.
