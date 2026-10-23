# ADR 0004: Workspace trust and privacy

- Status: Accepted
- Date: 2026-10-23

## Context

LocalMind can index files from the user's machine and send selected context to a
cloud model. The current active API accepts arbitrary filesystem paths and uses a
wildcard CORS policy. That is acceptable only for early local development, not
for a public product.

The trust boundary must be explicit: the user chooses which roots LocalMind may
read, and the backend enforces that choice.

## Decision

### Workspace boundaries

- Only explicitly registered/approved workspace roots may be read or indexed.
- Normalize paths before comparison and access.
- Block path traversal and symlink escapes outside approved roots.
- Use one central ignore policy for vendor, generated, hidden, lock, and
  oversized files.
- Enforce file-size, page-count, indexing-concurrency, and resource limits.

### Local API

- Bind to loopback by default.
- Replace wildcard CORS with an explicit allowlist before public beta.
- Add authentication for local clients; loopback alone is not an authorization
  boundary.
- Validate and bound all request inputs.

### Cloud context

- Cloud use is opt-in and visible.
- Send only selected evidence and minimal context.
- Allow excluding sensitive files and folders.
- Do not upload whole repositories or entire PDFs by default.
- Do not log raw document content or secrets by default.

### Untrusted content

- Documents, source files, READMEs, and repository instructions are data, not
  authority.
- Prompt injection cannot change tool permissions or workspace boundaries.
- Retrieved content is labeled as untrusted in advisor prompts.

## Consequences

- Indexing requires a workspace selection step; arbitrary path indexing becomes
  an internal/admin operation or is removed from the public API.
- Tests need temporary approved roots and must verify traversal/escape rejection.
- Existing indexes created from unapproved roots need a migration or explicit
  re-approval before they are searchable in the new model.
- The current wildcard CORS and unauthenticated API are known foundation gaps,
  tracked in LM-006 and the public-beta security audit.

## Open questions

- Whether the desktop app stores workspace approvals in SQLite, OS settings, or
  both.
- The local client authentication mechanism (token file, OS keychain, or
  per-launch secret).
- How to handle moved/deleted workspace roots without losing citations.
