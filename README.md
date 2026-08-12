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
- Short-lived, one-time confirmation tokens for sensitive commands
- Confirmation tokens are bound to the exact command and cannot be replayed
- Legacy `confirmed: true` is retained only for compatibility and never authorizes execution
- Durable command audit trail at `GET /audit`
- Secret redaction for common password, token, API-key, and secret labels before audit persistence
- Durable request idempotency for `POST /command` using optional caller-supplied `request_id`
- Request-ID collision protection: the same ID cannot be reused for a different command or confirmation token
- Automated API, safety, memory, persistence, routing, audit, idempotency, and confirmation tests
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

Try durable memory:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"remember my favorite editor is IntelliJ","request_id":"req-memory-0001"}'

curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"what do you remember"}'
```

Try a sensitive command:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"shutdown"}'
```

Vayu returns `confirmation_required` plus a short-lived `confirmation_token`. Resubmit the exact command with that token:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"shutdown","confirmation_token":"<token returned by Vayu>"}'
```

The token can be used only once, expires after five minutes, and cannot authorize another command. Vayu still will not execute `shutdown` until an explicit executor skill exists; successful confirmation only allows the request to advance to the skill boundary.

If a client retries a request with the same `request_id` and identical command/confirmation-token fingerprint, Vayu returns the cached response without executing the command or writing a second audit event. Reusing that ID with a different command or confirmation token returns HTTP `409 Conflict`.

## Runtime data

By default Vayu stores durable state in `data/vayu.db`. Override it with `VAYU_DB_PATH`.

Runtime databases and `.env` files are ignored by Git. Do not commit credentials or provider keys. Confirmation tokens are stored only as SHA-256 hashes, never in plaintext.

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
