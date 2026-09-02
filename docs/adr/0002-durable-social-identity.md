# ADR 0002: Durable social identity without durable secrets

- Status: Accepted
- Date: 2026-09-03

## Context

The first Social Media Organ intentionally kept account bindings in process memory. That failed closed after restart, but it also meant Vayu could not retain a stable account identity across restarts. Persisting OAuth tokens in the same SQLite database or proposed-action payload would solve continuity by weakening the security boundary.

## Decision

Vayu persists only non-secret social identity metadata: platform, account ID, adapter ID, optional logical credential-provider/key locator, revision, enabled/revoked state, and timestamps. Raw access tokens, refresh tokens, passwords, cookies, authorization headers, and browser sessions have no field in the social identity schema.

Credential references are deliberately constrained to logical provider/key identifiers. They are locators, not URI-shaped secrets or serialized credential blobs. A later credential-provider abstraction may resolve those references out of band, but the Social Media Organ database and proposed-action payloads remain secret-free.

Every binding has a monotonic revision. A social publish proposal records the revision it was reviewed against. Execution re-resolves the durable binding and rejects the action if the binding is revoked or its revision changed. An active binding cannot be silently repointed; it must be revoked before a different adapter or credential locator is bound.

Adapter registration remains process-local. After restart, durable identity may be known but publishing remains unavailable until the runtime explicitly installs the matching platform adapter. This preserves fail-closed startup behavior.

## Consequences

- Social account identity survives process restart.
- Revocation immediately prevents approved-but-not-yet-executed publishing.
- Rebinding invalidates approvals created against an older identity revision.
- Credential locators never enter social publish action payloads.
- Real OAuth lifecycle management is still not implemented; future official adapters need an out-of-band credential provider.
- A database compromise reveals account identifiers and credential locator names, but not OAuth material by design.
