# 2026-09-05 04:02 — Execution-time Social Credential Leasing

## Hypothesis

The highest-leverage next Social Media Organ increment is to connect the Credential Provider Cortex to social publishing only after Vayu has atomically claimed an approved `social.publish` action. That minimizes secret exposure while giving future official platform adapters a production-shaped credential path.

## Architectural context

Vayu is the BRAIN and coordinates specialist organs. KUPPA AI remains the HEART and human-facing identity/personality layer. Social publishing remains a consequential external action. Durable social account identity stores only non-secret credential locators, while the credential provider registry resolves secret material into short-lived process-local leases.

The previous validated baseline was `cf3a64a3dff4e0925a6fce4d9680cfcc565713cc` (`v2026.09.04`), whose `main` GitHub Actions CI run #254 completed successfully.

## Detailed changes

- Extended the social adapter contract with explicit `credential_scopes(account_id)` declarations.
- Added a separate credential-aware publish path receiving a short-lived `CredentialLease` rather than a raw durable token field.
- Added an optional `CredentialProviderRegistry` dependency to `SocialMediaOrgan`.
- Kept proposal-time handling secret-free: scope declarations are bounded/validated, but no provider resolution occurs while an action is `pending_approval`.
- Added execution-time credential resolution after the existing action executor has claimed an approved action.
- Required an explicit durable non-secret credential reference for adapters that declare publishing scopes.
- Required every declared scope to be available before provider resolution; insufficient scopes fail closed.
- Wrapped the credential-aware adapter call in the lease context manager so the lease is closed on both success and provider failure.
- Left credential-free mock adapters on the existing ordinary publish path.
- Kept credential references and secret values out of `social.publish` action payloads.
- Added ADR 0004 documenting the execution-time secret-resolution boundary.

## Files/components affected

- `app/social.py`
- `tests/test_social_credentials.py`
- `VERSION`
- `CHANGELOG.md`
- `docs/adr/0004-social-credential-resolution-boundary.md`
- `docs/evolution/README.md`
- `docs/evolution/2026/09/2026-09-05-0402-execution-time-social-credential-leasing.md`

## Before / after behavior

Before: Vayu had a provider-neutral credential registry and durable non-secret social credential references, but the Social Media Organ did not use them. Real OAuth-backed adapters therefore had no safe execution-time credential path.

After: a credential-requiring social adapter declares narrow scopes. Drafting and approval do not resolve secrets. Once an approved action is claimed for execution, Vayu validates the current durable account binding, obtains a short-lived scope-checked lease, invokes the credential-aware adapter path, closes the lease, and still requires a verified publish receipt before success is recorded.

## Tests/checks and results

The new regression module covers:

1. no credential resolution during proposal or an unauthorized execution attempt;
2. exactly one credential resolution after approval and claimed execution;
3. no credential/token material in the durable action payload;
4. missing required scope fails before secret resolution;
5. missing credential reference fails closed;
6. leases close after successful publishing;
7. leases also close after adapter/provider failure;
8. failed publish paths remain terminal `execution_failed` actions.

Validation result is recorded only after CI executes this commit. The pre-change known-good `main` baseline CI was successful.

## Metrics

No cognitive capability score is increased. This is a security/reliability and organ-infrastructure increment, not evidence of improved reasoning intelligence.

## Security / privacy / permission implications

Security boundary is stronger. Credential availability never implies publishing authority. Human approval, approval expiry, action payload policy, account/adaptor binding revision checks, atomic execution ownership, platform capability checks, idempotency, and verified publish receipts remain independent gates.

No OAuth token, access token, refresh token, password, cookie, or secret is added to repository code, SQLite schema, action payloads, audit context, or durable social identity.

## Failures/fallbacks tested

- unapproved execution: rejected before credential resolution;
- missing credential reference: fail closed;
- required scope unavailable: fail closed before provider resolution;
- adapter exception after credential resolution: action becomes `execution_failed` and lease is closed;
- credential-free adapters: continue to publish through the existing path without provider dependency.

## Rollback reference / procedure

Rollback to `cf3a64a3dff4e0925a6fce4d9680cfcc565713cc`. Reverting this commit removes execution-time credential leasing while preserving the v2026.09.04 provider-neutral credential subsystem and all earlier Social Media Organ safety boundaries.

## Known limitations

- No production OS Keychain, Vault, or cloud-secret provider exists yet.
- No OAuth acquisition, refresh, rotation, or revocation workflow exists yet.
- No official LinkedIn HTTP adapter exists yet.
- The current credential-aware adapter boundary passes an in-memory lease to adapter code; adapters are trusted components and must not retain or log revealed secret bytes.
- Python memory zeroization remains best-effort.

## Technical debt

- Add adapter conformance tests that prevent official adapters from retaining credential material.
- Add redacted structured observability around credential lease outcomes without provider keys or secrets.
- Introduce normalized platform error/rate-limit classifications before the first network adapter.

## Dependencies

- `app.credentials.CredentialProviderRegistry`
- `app.credentials.CredentialLease`
- durable `SocialCredentialReference`
- existing `ActionExecutorRegistry` approved-action claim boundary

## Follow-up work

Build the first official LinkedIn adapter behind this boundary using documented LinkedIn APIs, explicit OAuth scope/capability discovery, normalized rate-limit/error responses, verified post identifiers/permalinks, and deterministic sandbox tests. Production credential storage should remain provider-specific and external to Vayu persistence.

## Next evolution target

Official LinkedIn adapter skeleton plus normalized social adapter failure/rate-limit taxonomy, while keeping live network execution disabled unless a real credential provider and explicitly approved publish action are present.
