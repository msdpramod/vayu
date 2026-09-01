# Vayu Social Media Organ Foundation

## Date / cycle
2026-09-01 — Vayu Brain / Organ evolution

## Hypothesis
Vayu needs a first-class Social Media Organ that can eventually publish across multiple platforms without bypassing Vayu's existing approval, audit, and execution lifecycle.

## Architectural context
Vayu is the brain. KUPPA AI is the heart and human-facing identity. Social publishing belongs to Vayu as a specialist organ/capability. KUPPA may request or present social actions, while Vayu owns planning, policy, permission checks, adapter selection, execution, and verification.

## Changes
- Added `app/social.py` with a platform-neutral Social Media Organ.
- Added explicit adapter contracts rather than hardcoded platform implementations.
- Added initial platform identities for LinkedIn, Instagram, Facebook, X, and YouTube.
- Added disabled-by-default adapters so no platform can publish until an approved OAuth/API integration is configured.
- Registered social publish actions through Vayu's existing `ActionExecutorRegistry`.
- Required all social publish proposals to use `risk=confirm`.
- Added verification requirements: a real adapter must return a `post_id` or URL.
- Added tamper protection so the payload platform must match the registered executor platform.
- Initialized the Social Media Organ from `app/__init__.py` so its executor registrations are loaded with Vayu.
- Added tests for preview configuration, mandatory approval, platform mismatch rejection, and unverifiable publish-result failure.

## Behavior before
Vayu had a durable action approval/execution lifecycle but no dedicated social publishing organ or platform adapter boundary.

## Behavior after
Vayu has a social publishing capability boundary that can propose and execute platform-specific actions only after explicit approval. Real network publishing remains disabled until official platform adapters and credentials are configured.

## Files affected
- `app/social.py`
- `app/__init__.py`
- `tests/test_social.py`

## Security / privacy / permission impact
- Social publishing is treated as consequential external action.
- No OAuth tokens, passwords, cookies, or platform secrets are stored in source.
- No unofficial browser automation or session hijacking is introduced.
- Publishing remains approval-gated by Vayu's durable action lifecycle.

## Failure / fallback behavior
- Missing credentials/configuration: adapter reports `credentials_required` and publishing fails safely.
- Payload platform mismatch: execution fails and the action is marked failed.
- Adapter without verifiable `post_id`/URL: execution fails.
- Unapproved action: executor refuses to run.

## Validation status
Static integration was completed against Vayu's existing `ProposedActionStore` and `ActionExecutorRegistry` contracts. Automated tests were added in `tests/test_social.py`. Full CI results should be verified on the pull request before merge.

## Known limitations
- No real LinkedIn/Meta/X/YouTube OAuth adapters yet.
- No social scheduling, media upload pipeline, analytics ingestion, or automatic retry/rate-limit handling yet.
- No dedicated REST endpoint for social preview/platform health yet; generic Vayu actions can represent approved publish operations.

## Rollback
Revert the Social Media Organ branch/merge commit. Vayu's pre-existing action framework remains independent of the social module.

## Next evolution targets
1. Add a dedicated social API surface for platform health, preview, propose, and status.
2. Add official OAuth/token-provider abstractions with encrypted deployment-time secret handling.
3. Implement the first real platform adapter, preferably LinkedIn, with mocked tests before live credentials are connected.
4. Add idempotency keys, rate-limit awareness, retry/backoff, post verification, and analytics ingestion.
5. Add narrow, revocable pre-authorized publishing policies for workflows explicitly approved by the user.
