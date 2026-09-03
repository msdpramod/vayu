# ADR 0003: Provider-neutral short-lived credential leases

- Status: Accepted
- Date: 2026-09-04

## Context

Vayu's Social Media Organ now persists only non-secret provider/key locators. The next official platform adapter needs a way to obtain OAuth material without placing tokens in SQLite, action payloads, planner context, audit logs, or repository configuration. Coupling the Social Media Organ directly to one secret backend would also make the architecture brittle.

## Decision

Introduce a provider-neutral credential registry. Providers expose secret-free metadata inspection separately from secret resolution. Vayu resolves credential material only on demand into a short-lived in-memory `CredentialLease` with explicit scopes and an expiry capped to 15 minutes. The lease representation is redacted and supports explicit close/best-effort zeroization.

Provider registration is explicit and process-local. Durable state continues to contain only provider/key locators. Missing providers, unavailable scopes, expired credentials, metadata identity mismatches, and expired resolved credentials fail closed.

The initial `MemoryCredentialProvider` exists only for deterministic development and CI. Production providers for OS keychains or managed secret stores must implement the same contract; they must not change the action approval model.

## Consequences

- Official platform adapters can be added without teaching the Social Media Organ how to persist or own tokens.
- Credential health and scopes can be inspected without resolving secret material.
- Secret resolution can be delayed until the execution boundary in a future adapter integration.
- Vayu does not gain blanket publishing authority; credentials and approval remain independent gates.
- Python cannot guarantee physical memory erasure, so zeroization is best-effort rather than a cryptographic guarantee.
