# Changelog

## v2026.08.25

- Started the next daily Vayu cognitive development version.
- Added an attention-gated cognitive grounding layer connecting Perception -> Attention -> World Model without adding action authority.
- Bound each grounding candidate to the exact perception observation and attention decision by observation ID; mismatches fail closed.
- Added a configurable salience threshold so low-priority sensory evidence is not persisted as durable belief.
- Capped grounded confidence to the weaker of source-observation confidence and candidate confidence, preventing extractors from manufacturing stronger certainty than the evidence supports.
- Preserved modality/source/observation provenance in grounded World Model facts and reused the existing contradiction policy.
- Bounded grounding batches to 32 candidates and rejected duplicate observations.
- Added regression coverage for successful grounding, confidence capping, low-salience abstention, cross-observation rejection, duplicate rejection and batch limits.
- Raised perception evidence conservatively from 0.32 to 0.36 and world-model evidence from 0.36 to 0.40; no live sensors or free-form semantic understanding are claimed.
- Identified schema-constrained semantic extraction with abstention as the next high-leverage Perception target before live microphone/camera integration.

## v2026.08.24

- Started the next daily Vayu cognitive development version.
- Added a durable evidence-aware World Model with bounded entities, typed relationships, temporal facts, confidence and provenance.
- Added contradiction handling: stronger contradictory evidence supersedes the current belief while preserving history; weaker contradictory evidence is retained as historical evidence without replacing the current belief.
- Added stable entity identity/type enforcement, timezone-aware observation timestamps, bounded values/provenance, query caps and SQLite indexes.
- Kept the World Model cognition-only: no planner, executor, network, permission or action authority.
- Added regression coverage for persistence, relationships, high/low-confidence contradictions, evidence strengthening, invalid evidence and entity-type conflicts.
- Raised world-model evidence conservatively from 0.18 to 0.36; automatic grounding from perception/attention into entities and facts is not yet claimed.
- Identified Perception at 0.32 as the next weakest measured domain, with grounding into the World Model as the highest-leverage bridge before adding live sensors.

## v2026.08.23

- Started the next daily Vayu cognitive development version.
- Added a bounded Perception Cortex gateway for user text, voice, vision, browser, device and file observations.
- Normalized all sensory evidence into the existing attention boundary instead of giving individual adapters direct planning or execution authority.
- Added strict observation validation for IDs, sources, summaries, timezone-aware timestamps and `[0, 1]` evidence scores.
- Bounded perception batches to 64 observations, rejected duplicate IDs, and failed closed on observations more than 60 seconds in the future.
- Kept voice/user input as ordinary user-attention stimuli rather than privileged safety overrides.
- Added regression coverage for multimodal attention flow, duplicate IDs, clock skew, naive timestamps, batch limits and safety-override isolation.
- Raised perception evidence conservatively from 0.15 to 0.32 and attention from 0.38 to 0.42; no live microphone/camera/browser/device adapter capability is claimed.
- Identified the world model as the next highest-leverage cognitive dependency so attended observations can become durable entity/state knowledge.

## v2026.08.22

- Started the next daily Vayu cognitive development version.
- Added a bounded deterministic attention/salience controller as the prerequisite for future multimodal perception.
- Added typed stimuli with validated importance, urgency, novelty and confidence signals plus deterministic ranking and tie-breaking.
- Added interruption policy that requires both absolute salience and a margin over current focus, with a narrow high-confidence/high-urgency safety override.
- Bounded attention batches to 64 stimuli, rejected duplicate IDs, and kept the subsystem pure: no model calls, persistence, networking, tools or execution authority.
- Added regression coverage for ranking, uncertain novelty, ordinary interruption suppression, safety interruption, low-confidence safety rejection and resource bounds.
- Raised the evidence-backed attention baseline conservatively from 0.20 to 0.38 while leaving perception at 0.15 because live multimodal ingestion is still absent.
- Added dated evolution evidence documenting the hypothesis, regression gate, rollback point, lesson and next perception target.

## v2026.08.21

- Started the next daily Vayu development version.
- Added time-bounded human approvals with a default 15-minute TTL, configurable via `VAYU_APPROVAL_TTL_SECONDS`.
- Added a terminal `expired` lifecycle state and durable `expired_at` timestamp so stale approvals cannot trigger delayed side effects.
- Enforced approval freshness atomically at the execution-claim boundary before any allow-listed adapter can run.
- Added an in-place SQLite schema migration for existing Vayu databases so the new approval lifecycle remains backward-compatible.
- Added regression coverage proving stale approvals never invoke executors, fresh approvals still execute normally, and existing databases gain the new column safely.
- Added a proposal-only cognitive evolution engine that scores executive control, memory, reasoning, attention, world model, skills, safety, and perception using explicit evidence.
- Added conservative baseline capability signals, weakest-domain selection, human-review-required evolution proposals, regression tests, and cognitive-evolution architecture documentation.
- Preserved the KUPPA AI-inspired separation of intelligence from authority without introducing cross-repository runtime coupling.

## v2026.08.20

- Started the next daily Vayu development version.
- Added an atomic `approved -> executing` claim before any allow-listed adapter invocation so concurrent workers cannot execute the same approved action twice.
- Added terminal `execution_failed` state for ambiguous downstream failures; failed side effects are not implicitly retried because the external system may already have partially completed them.
- Preserved payload-policy validation and human approval while strengthening the execution boundary against duplicate side effects.
- Added concurrency regression coverage proving one and only one worker can own an approved action, plus failure-state and store-level claim tests.
- Reused the KUPPA AI-inspired intelligence-versus-authority separation without introducing any runtime dependency between repositories.

## v2026.08.19

- Started the next daily Vayu development version.
- Generalized planner-only payload validation into a shared action payload policy used by the durable action store and executor boundary.
- Direct action proposals now fail closed on oversized, deeply nested, non-JSON, secret-bearing, and executable-like payloads before persistence.
- Approved actions are revalidated immediately before an allow-listed executor is invoked, preventing stored-payload drift from bypassing the safety policy.
- Execution-time policy violations are durably recorded as `execution_failed` with `payload_policy_violation`, while the adapter is never called.
- Added regression coverage proving unsafe direct proposals are not stored and tampered approved payloads cannot reach an executor.
- Preserved the KUPPA AI-inspired separation of intelligence from authority while making the safety boundary independent of how an action was proposed.

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
- Added durable action lifecycle events for proposal, approval, rejection, execution failures, and successful allow-listed execution.
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
