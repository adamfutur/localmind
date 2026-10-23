"""Benchmark the legacy FAISS search engine.

Run from the repository root:
    py scripts/benchmark_search.py

The benchmark uses a temporary index, so it never touches data/faiss_index.bin.
"""
import argparse
import json
import os
import statistics
import tempfile
import time
from pathlib import Path

import faiss
import numpy as np

DOCS = [
    ("rust_notes.md", "Rust prevents data races at compile time through ownership, borrowing, and the Send and Sync traits. The borrow checker rejects aliased mutable references."),
    ("python_async.md", "Python asyncio runs cooperative coroutines on an event loop. Use asyncio.create_task to schedule concurrent tasks and await them with asyncio.gather."),
    ("sqlite_wal.md", "SQLite write-ahead logging improves concurrent read performance. Set journal_mode to WAL and use a busy timeout when multiple connections write."),
    ("faiss_notes.md", "FAISS IndexFlatL2 stores vectors in a flat array and performs exact nearest-neighbour search using squared L2 distance."),
    ("vector_cache.md", "An LRU cache for query embeddings avoids recomputing the same sentence vector and reduces repeated search latency."),
    ("tauri_notes.md", "Tauri applications use a Rust core and a webview frontend. The allowlist controls which native APIs the frontend may call."),
    ("docker_notes.md", "Docker containers package an application with its dependencies. Use multi-stage builds to keep the final image small."),
    ("postgres_notes.md", "PostgreSQL uses MVCC to allow concurrent transactions. An index on a filtered column can avoid sequential scans."),
    ("react_notes.md", "React state updates are batched. Use useEffect for synchronization with external systems and keep derived values out of state."),
    ("windows_paths.md", "Windows file paths use drive letters and backslashes. Path.home() returns the current user profile directory."),
]

QUERIES = [
    ("How does Rust avoid data races?", "rust_notes.md"),
    ("How do I run concurrent coroutines in Python?", "python_async.md"),
    ("How can SQLite handle concurrent readers?", "sqlite_wal.md"),
    ("What does FAISS IndexFlatL2 do?", "faiss_notes.md"),
    ("How can repeated query embeddings be cached?", "vector_cache.md"),
    ("How does Tauri secure native APIs?", "tauri_notes.md"),
    ("How do I keep a Docker image small?", "docker_notes.md"),
    ("How does PostgreSQL handle concurrent transactions?", "postgres_notes.md"),
    ("How does React batch state updates?", "react_notes.md"),
    ("Where does Path.home() point on Windows?", "windows_paths.md"),
]

FILLER = [
    "miscellaneous", "archived", "garden", "travel", "recipe", "music",
    "photograph", "weekend", "shopping", "weather", "hobby", "journal",
]


def _p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def _record(values):
    return {"median_ms": round(statistics.median(values), 3), "p95_ms": round(_p95(values), 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents", type=int, default=500)
    parser.add_argument("--queries", type=int, default=len(QUERIES))
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)
    os.environ["LOCALMIND_FAISS_INDEX_PATH"] = str(base / "faiss_index.bin")
    os.environ["LOCALMIND_DOCUMENTS_MAP_PATH"] = str(base / "documents_map.json")

    # Import after setting env so the engine loads/saves only the temp index.
    from backend.app.search import engine

    engine._index = faiss.IndexFlatL2(engine.DIM)
    engine._documents_map = {}
    engine._faiss_id_to_uid = {}
    engine.clear_query_cache()

    docs = list(DOCS)
    for i in range(max(0, args.documents - len(docs))):
        words = " ".join(FILLER[(i + j) % len(FILLER)] for j in range(5))
        docs.append((
            f"C:/bench/filler_{i:04d}.txt",
            f"Archived personal note number {i} about {words}. No technical content.",
        ))

    vectors = engine._embed_documents([content for _, content in docs])
    engine._index.add(np.array(vectors, dtype="float32"))
    for faiss_id, (path, content) in enumerate(docs):
        uid = f"{path}::chunk::0"
        engine._documents_map[uid] = {
            "file_path": path,
            "content": content,
            "faiss_id": faiss_id,
        }
        engine._faiss_id_to_uid[faiss_id] = uid

    queries = QUERIES[: args.queries]

    cold_embed, warm_embed, faiss_ms, map_scan_ms, map_direct_ms = [], [], [], [], []
    total_cold, total_warm = [], []
    recalled = 0
    parity_ok = True

    for query, expected in queries:
        # Cold embedding: clear the cache before every measurement.
        for _ in range(args.reps):
            engine.clear_query_cache()
            t0 = time.perf_counter()
            engine._embed_query(query)
            cold_embed.append((time.perf_counter() - t0) * 1000)

        # Warm embedding: one warm-up, then all cache hits.
        engine._embed_query(query)
        for _ in range(args.reps):
            t0 = time.perf_counter()
            engine._embed_query(query)
            warm_embed.append((time.perf_counter() - t0) * 1000)

        query_vec = np.array(engine._embed_query(query), dtype="float32").reshape(1, -1)
        for _ in range(args.reps):
            t0 = time.perf_counter()
            _, indices = engine._index.search(query_vec, args.k)
            faiss_ms.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            for faiss_id in indices[0]:
                next(
                    (uid for uid, info in engine._documents_map.items()
                     if info.get("faiss_id") == faiss_id),
                    None,
                )
            map_scan_ms.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            for faiss_id in indices[0]:
                engine._faiss_id_to_uid.get(int(faiss_id))
            map_direct_ms.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            engine.search_index(query, k=args.k)
            total_warm.append((time.perf_counter() - t0) * 1000)

        for _ in range(args.reps):
            engine.clear_query_cache()
            t0 = time.perf_counter()
            results = engine.search_index(query, k=args.k)
            total_cold.append((time.perf_counter() - t0) * 1000)

        paths = [
            engine._documents_map[uid]["file_path"]
            for uid in results
            if uid in engine._documents_map
        ]
        if any(expected in path for path in paths):
            recalled += 1

        # Cache + direct lookup must return exactly the same ordering as the
        # old linear scan for the same FAISS indices.
        _, indices = engine._index.search(query_vec, args.k)
        scan_ids = [
            uid for uid in (
                next(
                    (uid for uid, info in engine._documents_map.items()
                     if info.get("faiss_id") == faiss_id),
                    None,
                )
                for faiss_id in indices[0]
            ) if uid is not None
        ]
        direct_ids = [
            engine._faiss_id_to_uid.get(int(faiss_id))
            for faiss_id in indices[0]
        ]
        direct_ids = [uid for uid in direct_ids if uid is not None]
        if scan_ids != direct_ids or engine.search_index(query, k=args.k) != scan_ids:
            parity_ok = False

    result = {
        "config": {
            "documents": len(docs),
            "queries": len(queries),
            "repetitions": args.reps,
            "k": args.k,
            "cache_size": engine.QUERY_CACHE_SIZE,
        },
        "stages": {
            "embed_cold": _record(cold_embed),
            "embed_warm_cache_hit": _record(warm_embed),
            "faiss": _record(faiss_ms),
            "map_scan_old": _record(map_scan_ms),
            "map_direct_new": _record(map_direct_ms),
            "search_index_cold": _record(total_cold),
            "search_index_warm": _record(total_warm),
        },
        "recall_at_k": round(recalled / len(queries), 3),
        "result_parity_vs_old_scan": parity_ok,
    }

    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")

    tmp.cleanup()


if __name__ == "__main__":
    main()
