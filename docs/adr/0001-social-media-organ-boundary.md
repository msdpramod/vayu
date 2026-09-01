# Social Media Organ Boundary

Status: Accepted
Date: 2026-09-02

## Context

Vayu needs a first-class Social Media Organ without coupling the brain to LinkedIn, Instagram, Facebook, X, YouTube, browser sessions, or platform-specific credentials. Public publishing is a consequential external side effect and must remain behind the existing proposed-action approval and execution lifecycle.

## Decision

Introduce a platform-neutral Social Media Organ with explicit adapters. Each adapter declares a stable adapter ID, one platform, capability discovery, health, and a publish operation. Vayu binds an account to an adapter explicitly before it may stage a publish proposal.

All publish requests enter the existing `social.publish` proposed-action path with risk `confirm`. The Social Media Organ never approves its own actions. The allow-listed action executor calls the organ only after Vayu's existing human approval, expiry, atomic execution claim, and payload policy gates have passed.

Publish requests contain only non-secret execution material: platform, account ID, adapter ID, content, opaque media references, and an idempotency key. OAuth tokens, refresh tokens, passwords, cookies, API secrets, and browser session state are outside this contract and must be supplied by future adapter-specific credential providers.

A publish is successful only when the adapter returns a verified receipt with a stable post ID and verification evidence; a permalink is preferred when the platform can supply one. Unverified provider responses fail the action rather than being reported as success.

Account bindings are process-local in this initial increment. Restart therefore removes publishing readiness and fails closed. Durable identity binding and credential-reference lifecycle are follow-up work and must not persist raw secrets.

## Consequences

- Platform integrations remain modular and independently replaceable.
- Browser automation and scraping are not required by the architecture.
- KUPPA receives high-level organ events such as `connected`, `disconnected`, and `approval_required` instead of adapter internals.
- Duplicate approved actions can share an adapter-level idempotency key; compliant adapters are expected to return the same provider result rather than duplicate a post when supported.
- Future narrow automation policies can be inserted before approval without changing platform adapters, but no blanket authority exists today.
- Real platform adapters remain intentionally absent until official API/OAuth contracts and secret storage are designed and tested.

## Rejected alternatives

- Direct platform calls from planners: violates separation of intelligence and authority.
- Browser/session automation as the default: brittle and incompatible with least privilege.
- Storing OAuth tokens in action payloads or SQLite action records: unnecessarily exposes credentials and conflicts with secret-handling policy.
- Treating provider HTTP success as publishing proof: external systems can return ambiguous outcomes; Vayu requires explicit verification evidence.
