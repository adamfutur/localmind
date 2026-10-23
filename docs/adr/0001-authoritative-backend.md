# ADR 0001: Authoritative backend

- Status: Accepted
- Date: 2026-10-23

## Context

The repository contains two backend generations:

- `backend/server.py` with `backend/api`, `backend/core`, and `backend/db`.
- `backend/main.py` with `backend/app/api`, `backend/app/search`,
  `backend/app/indexing`, `backend/app/storage`, and `backend/app/watchers`.

The active desktop client calls `http://localhost:8001/api`, which is served by
`backend/server.py`. The README still contains stale instructions for
`python -m backend.app`, and `backend/main.py` can start a second app on
`0.0.0.0:8000`. The only active import from the legacy tree is
`backend/api/ask.py` importing `backend.app.llm.client`.

Running two APIs creates ambiguous ownership, duplicate indexing behavior, and
conflicting ports and database paths.

## Decision

1. `backend/server.py` is the single authoritative API for v2.
2. The active API contract is versioned under `/api` and binds to loopback by
   default on port `8001`.
3. `backend/main.py` and `backend/app` are legacy. They receive maintenance and
   security fixes only, not new product features.
4. Legacy code is isolated rather than deleted in one sweeping change.
5. Shared functionality still imported by the active backend, currently the LLM
   client, will move behind a new service/provider boundary incrementally.
6. Stale run instructions are removed or corrected in LM-003. No documentation
   may present the legacy backend as an alternative production startup path.

## Consequences

- One documented startup path and one API implementation to test.
- Existing legacy behavior remains available for reference during migration.
- The active `ask` route temporarily depends on a legacy import; this is an
  accepted migration debt, not permission to add new legacy features.
- LM-003 must update `README.md`, `AGENTS.md`, and startup scripts to agree with
  this ADR.
- LM-004 and LM-005 target the active SQLite/FAISS stack only.

## Follow-up

- Move the LLM client out of `backend/app` into the provider layer.
- Add an architecture check that prevents active modules from importing
  `backend.app`.
- Decide whether the legacy tree is archived, moved to a clearly named
  `legacy/` directory, or removed in a later major version.
