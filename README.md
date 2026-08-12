# Vayu

Vayu is a Jarvis-style personal assistant backend MVP focused on safe, explicit command execution.

## What works now

- FastAPI backend
- `GET /`, `GET /health`, `GET /skills`, `GET /tasks`, `GET /reminders`, `GET /reminders/due`, `GET /notifications`
- `POST /command` orchestration API
- `POST /reminders/dispatch` safely stages due reminders into a durable local notification outbox
- Safe allow-listed skills: greeting, service status, UTC time, durable local task management, and durable local reminders
- Durable task commands: `add task ...`, `list tasks`, and `complete task <id>`
- Durable reminder commands: `remind me at <ISO-8601 time> to <message>`, `list reminders`, and `dismiss reminder <id>`
- Reminder timestamps must include `Z` or an explicit timezone offset and are normalized to UTC
- Due reminders can be staged exactly once into a SQLite notification outbox; no OS, email, push, or shell side effect is invoked automatically
- Intent routing for memory and AI reasoning fallback
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
- Automated API, safety, memory, persistence, routing, audit, idempotency, confirmation, task, reminder, and notification-outbox tests
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
- http://localhost:8000/tasks
- http://localhost:8000/reminders
- http://localhost:8000/reminders/due
- http://localhost:8000/notifications

Try task management:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"add task review Vayu CI","request_id":"req-task-0001"}'

curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"list tasks"}'

curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"complete task 1"}'
```

Task operations are implemented as explicit local skills. They only mutate Vayu's SQLite state and do not invoke a shell or external OS command.

Try reminders:

```bash
curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"remind me at 2026-08-13T16:00:00+05:30 to review Vayu CI","request_id":"req-reminder-0001"}'

curl -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"list reminders"}'

curl http://localhost:8000/reminders/due
curl -X POST http://localhost:8000/reminders/dispatch
curl http://localhost:8000/notifications
```

Vayu normalizes reminder times to UTC and rejects timezone-less timestamps to avoid ambiguous scheduling. Dispatch only writes pending records into Vayu's local outbox and is idempotent per reminder. A future delivery adapter can consume that outbox under its own scoped permissions and confirmation policy.

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

1. Scoped notification delivery adapters with retries, acknowledgements, and dead-letter handling
2. Real external LLM provider integration with timeouts and error isolation
3. Voice input/output (STT/TTS)
4. Richer explicit skill registry and scoped permissions
5. Desktop agent with narrowly scoped executors
6. Browser control
7. Calendar/email integrations
8. Smart-home integrations
9. Long-term semantic memory and retrieval
10. Observability/metrics and structured tracing
11. Mobile/web UI

Vayu must never execute arbitrary shell commands directly. Every action capability should be an explicit skill with scoped permissions, confirmation rules, idempotency where side effects are possible, and an auditable outcome.
