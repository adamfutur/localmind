# LocalMind v2 Change Log

## v2 foundation branch — 2026-10-23

This branch starts Milestone 0 without discarding the existing search work. It
does not yet ship the v2 document chat, grounded answers, or VS Code extension.

### Added

- `ARCHITECTURE.md` with the v2 component boundaries, data/index lifecycle,
  security invariants, quality gates, and milestone mapping.
- ADRs for the authoritative backend, provisional cloud BYOK strategy,
  advisor-only behavior, workspace trust/privacy, and the desktop + VS Code
  client contract.
- A real `tests/` suite for content search, document extraction/filename intent,
  and API contract smoke tests.
- `pyproject.toml` with pytest and Ruff configuration.
- `backend/requirements-dev.txt` for test and lint dependencies.
- GitHub Actions CI for:
  - Ruff on the active backend and tests.
  - Pytest.
  - TypeScript checking and the desktop production build.

### Changed

- Kept the existing search-accuracy checkpoint:
  - FTS5 content search with prefix matching and code-friendly tokens.
  - PDF/DOCX/ODT text extraction.
  - CV/document intent handling for queries such as `mon cv`.
  - Vendor/generated path filtering.
  - Safer per-file indexing and Windows console logging.
- Sorted imports and applied low-risk modern Python syntax in the active backend.
- Made active backend error handling explicit with `raise ... from ...`.
- Added pytest/Ruff cache entries to `.gitignore`.

### Verification performed locally

```powershell
py -m ruff check backend tests
py -m pytest
cd desktop
npm run build
```

Results:

- Ruff: all checks passed.
- Pytest: 7 passed.
- Desktop: TypeScript and Vite production build passed.
- Manual regression scripts also passed:
  - `py -m scripts.test_content_search`
  - `py -m scripts.test_document_search`

The GitHub Actions workflow has been added but has not yet been observed on a
remote runner. Its first run on `origin/v2` is the final LM-002 check.

### Deliberately not done in this branch yet

- LM-003: README/startup cleanup and legacy backend isolation.
- LM-004: Alembic migrations and a baseline for existing SQLite data.
- LM-005: stable document/chunk IDs, chunk replacement, deletion cleanup, and
  idempotent retries.
- LM-006: workspace registration, path normalization, approved-root enforcement,
  local API authentication, and production CORS.
- Page-aware PDF citations, OCR, table extraction, grounded `/api/ask`, and the
  VS Code extension.

### Known state

- The active API is `backend/server.py` on `127.0.0.1:8001`.
- The root `README.md` still contains legacy sections that describe a different
  startup path and Rust-managed Python process. They are intentionally left for
  LM-003.
- The current index may contain stale or legacy vectors; it was not rebuilt or
  deleted as part of this branch.
- Cloud reasoning is a provisional architecture decision, not implemented
  functionality.
