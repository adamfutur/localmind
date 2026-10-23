# LocalMind — agent notes

Local-first RAG app: React/Vite UI + Tauri (Rust) shell in `desktop/`, FastAPI backend in `backend/`. Python is a separate process; the Tauri shell does **not** spawn or manage it.

## Commands (run from repo root)

```powershell
pip install -r backend/requirements.txt   # not the root requirements.txt
python -m backend.server                  # API on 127.0.0.1:8001, auto-reload
python check_db.py                        # verify SQLite tables/columns

cd desktop
npm install
npm run dev          # web UI only, http://localhost:1420
npm run tauri dev    # desktop app (Vite is started automatically)
npm run build        # tsc typecheck + vite build
```

- `.\scripts\start_localmind.bat` starts the backend plus the **web** UI (not Tauri); it also adds Cargo to `PATH`.
- No lint, test, or CI config exists. `npm run build` is the only frontend check.
- `python scripts/test_ollama.py` tests the LLM. `scripts/test_api.py` is stale: it calls port 8000 and needs `aiohttp`, which is not in requirements.
- `python scripts/benchmark_search.py` benchmarks the legacy search stages using a temporary index. `python scripts/test_search_concurrency.py` exercises concurrent add/search/remove across the 100/200-vector save thresholds.

## Which backend is live

- Active stack: `backend/server.py` → `backend/api/{search,index,ask}.py` → `backend/core` (FastEmbed/ONNX `all-MiniLM-L6-v2` by default, PyTorch fallback) → `backend/db` (SQLAlchemy, `data/metadata_v2.db`, `data/vectors.faiss`). LLM calls go through `backend/app/llm/client.py`.
- Legacy parallel stack: `backend/main.py` + `backend/app/api`, `app/search`, `app/indexing`, `app/storage`, `app/watchers` (port 8000, fastembed `BAAI/bge-small-en-v1.5`, `data/metadata.db`, `data/faiss_index.bin`). Only `backend.app.llm.client` is imported by the active server. The UI does not use this tree; keep changes there to maintenance/performance, not new features.
- README instructions (`python -m backend.app`, port 8000) are stale; `backend/app` has no entrypoint. Trust `backend/server.py` and `desktop/src/api.ts` (port **8001**).

## API and frontend contract

- `GET /api/search?q=&limit=`, `POST /api/ask` (`{question}`, max 2000 chars, 60s timeout, 256 output tokens), `POST /api/index?path=` (background), `POST /api/index-path?path=` (synchronous), `GET /api/search-status`, `GET /api/indexed-files`.
- `/api/index?path=` accepts `;`- or `,`-separated directories. Without `path` it scans `~/Documents` and `~/Desktop` — on this Windows checkout that includes the repo.
- `desktop/src/api.ts` hardcodes `http://localhost:8001/api`; `tauri.conf.json` CSP allows both 8000 and 8001. Keep them in sync if you change the port.
- The UI calls `GET /api/search` and renders file results; it does not call `/api/ask`. `/api/ask` remains available for optional LLM use.
- `HybridSearch` combines semantic hits with filename/path keyword matches and falls back to keyword-only if no embedding backend is available.

## Gotchas

- `/api/ask` requires Ollama at `http://localhost:11434` with the hardcoded `tinyllama` model (`backend/app/llm/client.py`). The UI is search-only, so Ollama is only needed for direct `/api/ask` calls. Connection failures are swallowed and returned as a normal 200 `answer` string, not an HTTP error. Override the model with `LOCALMIND_LLM_MODEL` (e.g. `qwen2.5:0.5b` is faster on low-end CPUs).
- The active ask route sends the raw question straight to the LLM; `backend/app/llm/qa.py` (retrieval-augmented prompting) is not used by it.
- Indexing is a FastAPI `BackgroundTask`: `/api/index` returns immediately. Watch server stdout or poll `/api/search-status`. Hidden/ignored directories, unsupported extensions, and files over `LOCALMIND_MAX_FILE_MB` are skipped before they reach SQLite.
- Modified files are re-embedded without deleting their old FAISS vectors, and deleted files are not pruned by the active indexer — the index accumulates stale chunks. A full rebuild is the only cleanup today (delete `data/vectors.faiss*` and re-index).
- Search `score` is raw FAISS L2 distance (lower is better), not similarity.
- `data/` is gitignored and created at import by `backend/config.py`; the SQLite schema is created when `backend/server.py` is imported. First run downloads the embedding model, and the model is loaded lazily on the first `/api/search` (not at server startup).
- Python 3.10+ is required (`str | None`, `list[str]` syntax). All `backend.*` imports require running from the repo root.
- `backend/services/*` are unused stubs.

## Performance knobs (8 GB / low-end CPU)

- `LOCALMIND_EMBED_BACKEND=auto|fastembed|sentence-transformers` — `auto` prefers FastEmbed/ONNX (lighter and faster); only install PyTorch if you need the fallback.
- `LOCALMIND_MAX_FILE_MB` (default 2), `LOCALMIND_VECTOR_SAVE_INTERVAL` (2000 vectors), `LOCALMIND_QUERY_CACHE_SIZE` (256 queries), `LOCALMIND_MAX_TOKENS` (256), `LOCALMIND_LLM_TIMEOUT` (60s), `LOCALMIND_LLM_MODEL`, `LOCALMIND_OLLAMA_KEEP_ALIVE` (30m), `LOCALMIND_OLLAMA_NUM_CTX` (1024), `LOCALMIND_OLLAMA_NUM_THREAD`.
- The index and embedding model are process-wide singletons; `VectorStore.save()` is batched and atomic. Do not call `save()` per file — that recreates the old O(n²) indexing behavior.
- Both `EmbeddingModel` (active) and `backend/app/search/engine.py` (legacy) cache query embeddings in a bounded LRU. Cache hits cost ~0.002–0.01 ms; misses are model-bound. The legacy engine uses a direct FAISS-id→UID map and an `RLock` (add/remove call `_save_index_and_documents()` while holding the lock).
- On the active stack, repeated-query latency is dominated by the SQLite keyword query (~4 ms median in the 500-doc benchmark), not the cached embedding or FAISS. If search latency matters next, cache keyword results or add SQLite FTS; do not add another semantic cache.
- `scripts/benchmark_search.py` writes machine-specific JSON with `--output`; `benchmarks/baseline.json` and `benchmarks/optimized.json` are examples from an i5-10210U / 7.8 GB machine with 500 synthetic docs. Use the script to reproduce, not the JSON as an absolute target.
- For chat latency, pull a smaller Ollama model (`ollama pull qwen2.5:0.5b`) and set `LOCALMIND_LLM_MODEL=qwen2.5:0.5b`; `tinyllama` is the default but still slow on 4-thread CPUs.
