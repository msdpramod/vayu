# ADR 0004: Resolve social credentials only inside claimed execution

- Status: Accepted
- Date: 2026-09-05

## Context

Vayu already separates durable social account identity from secret material and exposes short-lived credential leases through a provider-neutral registry. The remaining risk is *when* credentials are resolved. Resolving OAuth material while drafting, validating, previewing, or waiting for human approval would unnecessarily widen secret exposure and could let future code accidentally treat credential availability as publishing authority.

## Decision

Social platform adapters explicitly declare the credential scopes required for publishing. Proposal-time code may validate the declared scope shape, but it must not resolve secret material. Credential resolution is permitted only from `SocialMediaOrgan.execute_publish_payload`, which is invoked by Vayu's `ActionExecutorRegistry` after an approved action has been atomically claimed for execution.

If an adapter requires scopes, the durable account binding must contain a non-secret `SocialCredentialReference`, a credential provider registry must be installed, and the provider must satisfy every required scope. Vayu then creates a short-lived `CredentialLease` in a context manager and passes that lease only to the credential-aware adapter publish method. The lease is closed on both success and exception paths.

Credential-free adapters continue to use the ordinary publish method and do not trigger credential resolution. Credential references and secret material never enter the proposed-action payload.

## Consequences

- Drafting and approval cannot expose or resolve social OAuth secrets.
- Approval remains necessary but is still not sufficient: account binding, adapter identity, scopes, provider availability, credential validity, and publish verification are rechecked at execution.
- Credential leases have a smaller lifetime and failure surface and are reliably closed when adapters fail.
- Official platform adapters can request narrowly scoped credentials without owning durable token storage.
- Adapter contracts gain explicit credential-scope declaration and a credential-aware publish path.
- This does not implement OAuth acquisition/refresh or a production LinkedIn HTTP adapter; those remain separate future increments.
