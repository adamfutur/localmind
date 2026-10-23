# ADR 0005: Desktop and VS Code clients

- Status: Accepted
- Date: 2026-10-23

## Context

LocalMind already has a React + Tauri desktop client. The v2 plan adds a VS Code
extension. If each client implements its own retrieval, citation, or advisor
logic, behavior will diverge and security rules will be harder to enforce.

## Decision

- Both clients use the same versioned local API.
- The backend owns retrieval, ranking, citations, provider calls, advisor
  orchestration, policy checks, and session state.
- Clients own presentation: search UI, document library, preview, citations,
  plans, findings, and proposal rendering.
- Clients do not duplicate business logic or call model providers directly.
- The VS Code extension is a thin API client. It must handle backend
  disconnection, timeouts, and version mismatches gracefully.
- The extension respects VS Code workspace trust. It does not read files outside
  the opened workspace and does not apply proposed changes.
- The first extension commands are explain-selection, ask-about-workspace, and
  search-repository, all read-only.

## Consequences

- API contracts must be explicit, typed, and versioned before the extension ships.
- A backend change can affect both clients; CI must cover the shared contract.
- Desktop and extension can be released independently, but they share a
  compatibility policy.
- The desktop app remains the full document workspace; the extension focuses on
  code-context workflows.

## Follow-up

- Define the versioned request/response schemas and error envelope.
- Add contract tests shared by both clients.
- Add a local API authentication handshake for the extension.
- Test activation, workspace trust, disconnections, path boundaries, and
  proposal rendering.
