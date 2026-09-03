# 2026-09-04 04:00 — Credential Provider Cortex

## Hypothesis

The highest-leverage next Social Media Organ increment is not a LinkedIn-specific HTTP client yet. A real adapter first needs a provider-neutral way to inspect scopes/expiry and resolve OAuth material only at execution time without persisting or logging secrets.

## Architectural context

Vayu remains the BRAIN and KUPPA AI remains the HEART. Social publishing is a consequential external action behind Vayu's existing approval and executor gates. The durable social identity layer added in v2026.09.03 stores only non-secret provider/key locators.

## Detailed changes

- Added `CredentialProviderRegistry` for explicit process-local provider registration.
- Separated secret-free `inspect` from secret-bearing `resolve`.
- Added bounded scope validation and fail-closed checks for missing providers, missing scopes, expired credentials, and mismatched metadata.
- Added short-lived `CredentialLease` objects capped to 15 minutes, with redacted representation, explicit scope checks, context-manager cleanup, and best-effort byte-buffer zeroization.
- Added deterministic process-local `MemoryCredentialProvider` for CI/development only.
- Kept the contract structural so existing `SocialCredentialReference(provider, key)` values can be used without a cross-module persistence dependency.
- Added ADR 0003.

## Files/components affected

- `app/credentials.py`
- `tests/test_credentials.py`
- `docs/adr/0003-provider-neutral-credential-leases.md`
- `docs/evolution/2026/09/2026-09-04-0400-credential-provider-cortex.md`
- `docs/evolution/README.md`
- `CHANGELOG.md`
- `VERSION`

## Before / after

Before: Vayu could persist a non-secret credential locator but had no contract for checking scopes/expiry or resolving the referenced material safely.

After: any organ can register a credential provider, inspect non-secret metadata, and request a short-lived scoped in-memory lease. No token storage field or action-payload field is introduced.

## Tests/checks

Added regression coverage for secret-free inspection, scope-aware denial before secret resolution, short-lived leases, redacted representations, close/context cleanup, expired credentials, duplicate/missing providers, lease-duration bounds, and provider-expiry lease capping.

GitHub Actions CI is the authoritative regression gate for this change. This record must be updated only with validated results; no pass count is claimed before CI completes.

## Metrics

No cognitive capability score is increased. This is infrastructure/safety capability, not evidence of stronger reasoning.

## Security / privacy / permission implications

Security boundary is stronger. Durable state still contains only locators. Raw credentials remain provider-owned until explicitly leased. A credential lease grants no action approval and does not bypass `social.publish` confirmation, approval expiry, idempotency, or executor ownership.

## Failures / fallbacks tested

- Provider not registered -> fail closed.
- Required scope unavailable -> fail closed before resolution.
- Metadata or resolved credential expired -> fail closed.
- Lease closed or expired -> secret unavailable.
- Duplicate provider registration -> rejected.

## Rollback

Known-good rollback reference before this evolution: `8021795960b91d899c8323da4a42949f1c32462e` (v2026.09.03). Revert this evolution commit to remove the credential-provider boundary.

## Known limitations / technical debt

- No OS Keychain, Vault, AWS/GCP/Azure secret-manager provider exists yet.
- No OAuth refresh/rotation workflow exists yet.
- `MemoryCredentialProvider` is not a production secret store.
- Python memory zeroization is best-effort.
- Social adapters are not yet wired to request leases at execution time.

## Dependencies

Python standard library only.

## Follow-up work

Wire the Social Media Organ execution path to resolve a `social.publish` scoped lease only after an approved action is claimed for execution, then add an official LinkedIn adapter using the provider contract.

## Next evolution target

Execution-time Social Media Organ credential leasing + official LinkedIn adapter skeleton with OAuth scope/capability discovery and verified publish-response parsing.
