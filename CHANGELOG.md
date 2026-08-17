# Changelog

## v2026.08.18

- Started the next daily Vayu development version.
- Added a dedicated planner payload policy that fails closed on oversized, deeply nested, non-JSON, secret-bearing, and executable-like fields before proposals are persisted.
- Added hard payload limits: 8 KiB serialized size, four nesting levels, and bounded collection sizes.
- Blocked planner payload fields such as credentials, tokens, passwords, secrets, shell, script, executable, and subprocess to reduce prompt-injection and tool-smuggling risk.
- Added regression tests covering safe payloads, secret/execution-field rejection, excessive depth, and oversized payloads.
- Kept the existing KUPPA AI-inspired separation of intelligence from authority: planner output remains proposal-only and still requires human approval before execution.

## v2026.08.17

- Started the next daily Vayu development version.
- Added an isolated Ollama planner provider using strict JSON output, explicit timeouts, and no executor/approval capability.
- Added environment-based planner selection with `VAYU_PLANNER_PROVIDER`, `VAYU_OLLAMA_URL`, `VAYU_OLLAMA_MODEL`, and `VAYU_OLLAMA_TIMEOUT_SECONDS`.
- Kept planner-created actions behind the same allow-list and mandatory `confirm` risk boundary.
- Added fail-closed validation for unsupported planner fields, malformed responses, transport failures, and unsafe tool proposals.
- Added planner regression tests for valid Ollama proposals, rejected extra execution fields, and offline transport failures.
- Made `/plan` return HTTP 503 when the configured planner provider is unavailable instead of surfacing an unhandled server error.
- Reused KUPPA AI's local-intelligence pattern while keeping Vayu independently runnable and free of cross-repository runtime coupling.

## v2026.08.16

- Started the next daily Vayu development version.
- Added a structured planner boundary that can propose allow-listed actions but has no execution authority.
- Added planner decision validation so unknown tools, malformed payloads, and unsafe multi-action output fail closed.
- Kept every planner-created action in `pending_approval`; the planner cannot approve or execute its own proposal.
- Added deterministic local fallback planning plus provider abstractions for future LLM-backed planners without coupling Vayu to KUPPA AI at runtime.
- Added planner unit/API regression coverage and updated architecture documentation.

## v2026.08.15

- Started the next daily Vayu development version.
- Reused KUPPA AI's human-in-the-loop proposed-action pattern without creating a runtime dependency between repositories.
- Added durable proposed actions with explicit `pending_approval`, `approved`, `rejected`, and `executed` lifecycle states.
- Added a hard execution gate and allow-listed executor registry; unapproved actions and unknown adapters fail closed.
- Added durable action lifecycle events for proposal, approval, rejection, execution failures, and successful execution.
- Added action proposal/list/detail/event plus approve, reject, and execute APIs.
- Added unit and API regression tests covering pre-approval blocking, terminal rejection, missing adapters, durable events, and successful allow-listed execution.
- Documented the planner-versus-executor boundary so future LLM, email, calendar, browser, desktop, and smart-home integrations cannot bypass human approval.

## v2026.08.13

- Started the next daily Vayu development version.
- Wired durable request idempotency into `POST /command`.
- Added exact-retry replay without duplicate execution or duplicate audit entries.
- Added HTTP 409 protection when a request ID is reused for a different command or confirmation state.
- Added API regression tests and documented client retry behavior.
- Replaced boolean-only sensitive-action confirmation with short-lived, one-time confirmation tokens.
- Bound confirmation tokens to the exact command, stored only token hashes, and prevented replay.
- Kept legacy `confirmed` input for compatibility while removing its authority to approve execution.
- Added persistence, replay, cross-command, API-flow, and idempotency regression tests for confirmations.
- Repaired GitHub Actions test execution and updated a stale confirmation regression expectation; CI returned green with 36 passing tests before feature work resumed.
- Added durable SQLite-backed local tasks with explicit `task_add`, `tasks`, and `task_complete` skills.
- Added `GET /tasks`, command-level task workflows, persistence tests, and explicit-skill registry coverage.
- Added durable timezone-aware reminders with explicit `reminder_add`, `reminders`, and `reminder_dismiss` skills.
- Added `GET /reminders` and read-only `GET /reminders/due` APIs as the safe foundation for future notifier adapters.
- Normalized reminder timestamps to UTC, rejected ambiguous timezone-less scheduling, indexed due-reminder queries, and added persistence/API/due-state regression tests.
- Added a durable, idempotent local notification outbox that stages due reminders exactly once without invoking external or OS side effects.
- Added `POST /reminders/dispatch` and `GET /notifications` plus persistence and duplicate-dispatch regression tests.

## v2026.08.12

- Added durable SQLite-backed conversation memory and wired it into `/command`.
- Connected intent routing and the safe AI-provider fallback to the live orchestration path.
- Added `/memory` plus persistence and routing regression tests.
- Added a durable command audit trail covering blocked, confirmation-required, successful, memory, and AI-fallback decisions.
- Added redaction for common password, token, API-key, and secret labels before audit persistence.
- Added `/audit` plus audit persistence, safety, and redaction tests.
- Added a durable idempotency store for caller request IDs so retried commands can be deduplicated safely.
- Added persistence, collision, and reset tests for the idempotency layer.
- Updated runtime documentation and ignored local database files.

## v2026.08.11

- Established FastAPI assistant core and health endpoints.
- Added explicit skill registry and permission/risk classification.
- Added confirmation boundary for sensitive operations.
- Added intent routing and bounded conversation memory foundation.
- Added API and safety tests.
- Added Docker and GitHub Actions CI.
- Started date-based daily Vayu development versions.
