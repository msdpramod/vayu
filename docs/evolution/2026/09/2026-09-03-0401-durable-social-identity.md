# 2026-09-03 04:01 — Durable Social Identity

## Hypothesis

The Social Media Organ cannot become a reliable Jarvis-style organ while account identity disappears on every restart. Persisting non-secret identity metadata, with binding revision checks and explicit revocation, should improve continuity without weakening the existing approval or secret-handling boundaries.

## Architectural context

Vayu remains the brain and coordinator. KUPPA remains the human-facing heart. Social publishing is still a consequential external action routed through the existing proposed-action approval lifecycle. This increment changes identity continuity only; it does not add blanket automation authority or a real platform credential.

The previous Social Media Organ foundation kept account bindings process-local and identified durable non-secret identity plus credential-reference lifecycle as the next production gap.

## Detailed changes

- Added `app/social_identity.py` with a SQLite-backed `SocialAccountStore`.
- Persisted platform, account ID, adapter ID, optional non-secret credential locator, monotonic revision, enabled/revoked state, and timestamps.
- Added `SocialCredentialReference(provider, key)` with a deliberately narrow logical identifier grammar so URI-shaped/serialized token material is rejected.
- Wired `SocialMediaOrgan` to durable binding state using the same Vayu database path by default.
- Added account revocation and restart-safe status resolution.
- Kept adapter registration process-local so restart still fails closed until an adapter is explicitly installed.
- Added binding revision to `social.publish` proposed-action payloads.
- Revalidate binding revision and enabled state immediately before adapter execution so revocation/rebinding invalidates older approvals.
- Prevented an active account binding from being silently repointed to a different adapter or credential locator; explicit revocation is required first.
- Kept credential references out of publish action payloads.
- Added regression coverage for restart persistence, no-secret schema, credential-reference rejection, credential payload isolation, revocation after approval, stale approval after rebind, and silent-repoint prevention.

## Files/components affected

- `app/social.py`
- `app/social_identity.py`
- `tests/test_social_identity.py`
- `docs/adr/0002-durable-social-identity.md`
- `docs/evolution/2026/09/2026-09-03-0401-durable-social-identity.md`
- `docs/evolution/README.md`
- `VERSION`
- `CHANGELOG.md`

## Before / after

Before: social account bindings existed only in process memory. Restart removed publishing readiness and account identity continuity.

After: account identity metadata survives restart. Publishing still fails closed until the expected adapter is installed and healthy. Approved actions are pinned to the identity revision reviewed by the user.

## Tests/checks and results

Validation is performed through GitHub Actions because this execution environment cannot resolve `github.com` for an independent local clone. The feature branch adds targeted social identity regression tests and is merged only after the complete repository CI gate succeeds.

## Metrics

No cognitive capability score is increased. This is a reliability/security/organ-continuity increment, not evidence of improved reasoning capability.

## Security / privacy / permission implications

- No raw OAuth/access/refresh token, password, cookie, browser session, or authorization header storage was added.
- Credential references are non-secret locators only and are not copied into consequential-action payloads.
- Existing human approval, approval expiry, payload policy, atomic execution claim, execution failure state, and adapter verification boundaries remain unchanged.
- Revocation and binding revision checks make approved actions fail closed if account identity changes before execution.
- No new execution authority is granted to Vayu or KUPPA.

## Failures/fallbacks tested

- Known binding but missing runtime adapter => disconnected/fail closed.
- Revoked binding after approval => publish blocked before adapter call.
- Rebound identity after approval => stale approval rejected before adapter call.
- URI-shaped or bearer-like credential locator => rejected at construction.
- Active binding repoint attempt => rejected until explicit revocation.

## Rollback

Known-good baseline: `1487a54f742f6f82ab05f58b058eaed5f08f198f` (`v2026.09.02`). Roll back the squash merge to restore process-local account binding behavior. The added SQLite table is additive and can remain unused after rollback.

## Known limitations

- No real OAuth/token acquisition, refresh, rotation, expiry, or revocation provider exists yet.
- No official LinkedIn/Instagram/Facebook/X/YouTube adapter exists yet.
- Adapter registration remains process-local.
- Account binding administration is not yet exposed through a dedicated permissioned API.
- Durable platform capability/health snapshots are not yet stored.

## Technical debt / dependencies

A future credential provider must guarantee that resolved secret material is short-lived in memory, never serialized into action/audit payloads, and never logged. Official platform adapters should depend on that provider interface instead of environment-specific token loading inside social logic.

## Follow-up work

- Add an explicit credential-provider protocol with secret-safe resolution and token lifecycle metadata.
- Add durable capability/health snapshots with freshness timestamps.
- Implement the first official LinkedIn adapter behind the existing binding/approval/idempotency/verification contract.
- Add account-binding management APIs with least-privilege permission checks.

## Next evolution target

Credential-provider abstraction plus a sandboxed official-API-shaped LinkedIn adapter contract, without introducing real credentials until the lifecycle and redaction boundaries are testable end to end.
