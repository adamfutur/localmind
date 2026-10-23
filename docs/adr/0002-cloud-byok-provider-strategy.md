# ADR 0002: Cloud reasoning and BYOK

- Status: Proposed
- Date: 2026-10-23

## Context

The current `/api/ask` route calls a local Ollama endpoint. The v2 product needs
stronger reasoning than a small mandatory local model can provide on an 8 GB
machine. The handoff proposes cloud reasoning, starting with bring-your-own-key
(BYK), but explicitly does not treat that as a permanent product decision.

Cloud use changes the privacy model: document content and code may leave the
machine. The product must make that flow visible, minimize context, and keep
credentials out of application data.

## Decision

- Design for a typed provider interface rather than a concrete vendor SDK in the
  domain layer.
- Start with BYOK: the user supplies a provider key; LocalMind does not operate
  a model service by default.
- Store BYOK credentials in the operating system credential store. Never store
  them in logs, URLs, ordinary database columns, frontend local storage, or
  committed files.
- Provider features required by the interface: request/response typing, timeout,
  token limit, normalized errors, streaming, and cancellation.
- Cloud calls are opt-in. The UI must show what context will be sent and allow
  excluding sensitive files/folders.
- Send the minimum context: selected evidence, cited snippets, and task
  instructions. Do not upload whole repositories or entire PDFs by default.
- A hosted LocalMind service may be added later only through a new ADR that
  describes data handling, retention, and user consent.

## Consequences

- The product works without a local LLM, but requires a user-provided key for
  cloud reasoning.
- Provider-specific code stays behind an adapter, so changing vendors does not
  change retrieval, citations, or advisor policy.
- Offline search and document intelligence remain functional without cloud
  access.
- The current Ollama code is a local provider candidate, not the architecture.
- Tests must use fake providers and must never call a real cloud API.

## Open questions

- Which provider or providers ship first.
- Exact context preview and consent UI.
- Whether a hosted service will exist, and under what privacy terms.
- Retention and logging policy for provider errors.
