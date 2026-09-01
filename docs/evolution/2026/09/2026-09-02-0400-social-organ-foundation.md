# Evolution Record — Social Media Organ Foundation

Date/time: 2026-09-02 04:00 Asia/Kolkata
Topic: social-media-organ-foundation
Baseline: `a718d7cdbca953385a2ec0fd6ae2c08a1d382492`

## Hypothesis

Vayu cannot safely evolve toward a Jarvis-style social capability by adding platform-specific posting code directly into planners or generic executors. The highest-leverage first increment is a platform-neutral organ boundary that makes account identity, capabilities, approval, idempotency, verification, health, and KUPPA-facing state explicit before any real OAuth-backed adapter is introduced.

## Architectural context

Vayu remains the brain and coordinator. KUPPA remains the human-facing heart. The Social Media Organ is a specialist organ coordinated by Vayu. It does not inherit planner authority, approval authority, credentials, or unrestricted network access. Public publishing stays behind the existing proposed-action lifecycle.

## Detailed changes

- Added `app/social.py` with `SocialPlatform`, `SocialCapabilities`, `SocialAccountBinding`, `SocialPublishRequest`, `PublishReceipt`, `SocialHealth`, and `SocialOrganEvent` contracts.
- Added a `SocialPlatformAdapter` protocol for capability discovery, health, and verified publish operations.
- Added `SocialMediaOrgan` adapter registration and explicit platform/account binding.
- Added approval-gated `social.publish` proposal staging through `ProposedActionStore` with `risk=confirm`.
- Added execution-time revalidation of account binding, adapter identity, health, content bounds, media capability, and idempotency key before the adapter is called.
- Added publish-receipt verification so an unverified provider response becomes `execution_failed` rather than false success.
- Added `MockSocialAdapter`, a deterministic no-network CI/local fallback with adapter-level idempotency.
- Added high-level KUPPA-facing organ events for `connected`, `disconnected`, and `approval_required` states.
- Added ADR `docs/adr/0001-social-media-organ-boundary.md`.

## Files/components affected

- `app/social.py`
- `tests/test_social.py`
- `docs/adr/0001-social-media-organ-boundary.md`
- `docs/evolution/README.md`
- `docs/evolution/2026/09/2026-09-02-0400-social-organ-foundation.md`

## Before / after

Before: Vayu had no Social Media Organ, no social platform adapter contract, no social account identity binding, and no verified publish abstraction.

After: Vayu can stage a platform-neutral social publish as a normal consequential action, refuse unbound/disconnected accounts, route an approved action only to the explicitly bound adapter, demand verification evidence, and exercise the complete boundary using a deterministic mock without network credentials.

## Tests/checks

Baseline validation: GitHub Actions CI run #219 for baseline `a718d7cd` completed successfully.

New regression coverage added for:
- publishing cannot execute before explicit approval;
- approved publishing returns a verified post receipt;
- duplicate idempotency keys reuse the same mock provider receipt;
- disconnected platforms fail before a proposal is stored;
- unsupported media and oversized text fail closed;
- unverified provider outcomes become terminal execution failures;
- account bindings cannot cross platforms.

Post-change validation is performed on the evolution branch by GitHub Actions before promotion to `main`. Local clone/test execution is unavailable in this runtime because DNS cannot resolve `github.com`; this limitation does not affect GitHub Actions validation.

## Metrics

No cognitive capability score is raised in this commit. The measurable increment is the new six-case social regression suite plus explicit adapter/approval/verification contracts. A score increase would be premature before a real official platform adapter and durable identity binding exist.

## Security / privacy / permissions

- Social publishing remains a `confirm` external action.
- The organ cannot approve its own proposal.
- No token, OAuth credential, password, cookie, API secret, or browser session is accepted by the publish contract.
- Action payloads contain only non-secret content and opaque media references.
- Adapter/account identity is checked again at execution time to prevent approved-action rerouting after approval.
- Unverified external outcomes fail closed.

## Failures / fallbacks tested

- disconnected adapter;
- unsupported capability;
- oversized content;
- platform/account mismatch;
- unverified publish receipt;
- duplicate platform idempotency key.

The no-network mock adapter is the supported local/CI fallback.

## Rollback

Known-good rollback reference: `a718d7cdbca953385a2ec0fd6ae2c08a1d382492`.

Rollback procedure: move `main` back to the known-good reference if the new social boundary causes a regression. No schema migration or durable social state is introduced, so rollback does not require data migration.

## Known limitations

- Account bindings are process-local and deliberately fail closed after restart.
- No real LinkedIn/Instagram/Facebook/X/YouTube adapter is installed yet.
- No OAuth/token lifecycle provider exists yet.
- Media references are opaque; upload orchestration is not implemented.
- Scheduling, analytics ingestion, retries/backoff, rate-limit state, and narrow pre-authorization policies remain future work.

## Technical debt / dependencies

Future official adapters need a credential-reference abstraction, durable non-secret identity binding, adapter-specific rate-limit/health telemetry, and platform API contract tests. Secrets must live outside repository/action persistence.

## Next evolution target

Add durable non-secret social account identity binding plus a credential-provider reference interface and capability/health snapshot persistence, still without storing raw tokens. Then implement a LinkedIn sandbox/official adapter contract behind the same boundary before enabling any real publish call.
