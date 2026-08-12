# Changelog

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
