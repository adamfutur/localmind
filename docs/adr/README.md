# Architecture Decision Records

These ADRs capture durable v2 decisions. They are intentionally narrow: each
record states the context, the decision, and the consequences. Open questions
stay in `ARCHITECTURE.md` until they are resolved.

| ADR | Title | Status |
| --- | --- | --- |
| 0001 | [Authoritative backend](0001-authoritative-backend.md) | Accepted |
| 0002 | [Cloud reasoning and BYOK](0002-cloud-byok-provider-strategy.md) | Proposed |
| 0003 | [Advisor-only tools](0003-advisor-only-tools.md) | Accepted |
| 0004 | [Workspace trust and privacy](0004-workspace-trust-and-privacy.md) | Accepted |
| 0005 | [Desktop and VS Code clients](0005-desktop-and-vscode-clients.md) | Accepted |

## Status meanings

- **Proposed:** direction is being designed; implementation may proceed only
  behind a clean boundary.
- **Accepted:** implementation should follow the decision; changing it requires a
  new or superseding ADR.
- **Superseded:** retained for history; a later ADR replaces it.
