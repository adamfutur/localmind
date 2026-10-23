"""Concurrency smoke test for the legacy search engine.

Run from the repository root:
    py scripts/test_search_concurrency.py

It indexes across the 100/200 save thresholds while searches run, then removes
a file. The old non-reentrant lock deadlocked in both paths.
"""
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOTAL_DOCS = 240
WRITERS = 6
READERS = 4


def main():
    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)
    os.environ["LOCALMIND_FAISS_INDEX_PATH"] = str(base / "faiss_index.bin")
    os.environ["LOCALMIND_DOCUMENTS_MAP_PATH"] = str(base / "documents_map.json")

    from backend.app.search import engine

    import faiss

    engine._index = faiss.IndexFlatL2(engine.DIM)
    engine._documents_map = {}
    engine._faiss_id_to_uid = {}
    engine.clear_query_cache()

    stop = threading.Event()
    errors = []

    def writer(worker_id):
        start = worker_id * (TOTAL_DOCS // WRITERS)
        end = TOTAL_DOCS if worker_id == WRITERS - 1 else (worker_id + 1) * (TOTAL_DOCS // WRITERS)
        for i in range(start, end):
            try:
                engine.add_document_to_index(
                    f"Document {i} about topic {i % 17} with unique marker {i}.",
                    f"C:/concurrency/doc_{i}.txt::chunk::0",
                    f"C:/concurrency/doc_{i}.txt",
                )
            except Exception as exc:
                errors.append(f"writer {worker_id}: {exc}")

    def reader():
        queries = ["unique marker 42", "topic 7", "document contents"]
        while not stop.is_set():
            try:
                engine.search_index(queries[int(time.perf_counter() * 1000) % len(queries)], k=5)
            except Exception as exc:
                errors.append(f"reader: {exc}")

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WRITERS + READERS) as pool:
        reader_futures = [pool.submit(reader) for _ in range(READERS)]
        writer_futures = [pool.submit(writer, i) for i in range(WRITERS)]
        for future in writer_futures:
            future.result(timeout=120)
        stop.set()
        for future in reader_futures:
            future.result(timeout=30)

    elapsed = time.perf_counter() - started

    if errors:
        raise SystemExit("FAILED: " + " | ".join(errors[:5]))
    if engine._index.ntotal != TOTAL_DOCS:
        raise SystemExit(f"FAILED: expected {TOTAL_DOCS} vectors, got {engine._index.ntotal}")
    if len(engine._documents_map) != TOTAL_DOCS:
        raise SystemExit(f"FAILED: expected {TOTAL_DOCS} documents, got {len(engine._documents_map)}")
    if len(engine._faiss_id_to_uid) != TOTAL_DOCS:
        raise SystemExit("FAILED: direct id map is out of sync")

    # Removal used to deadlock because it re-entered the same non-reentrant lock.
    engine.remove_document_from_index_by_file_path("C:/concurrency/doc_0.txt")
    if engine._index.ntotal != TOTAL_DOCS - 1:
        raise SystemExit(f"FAILED: removal left {engine._index.ntotal} vectors")
    if len(engine._documents_map) != TOTAL_DOCS - 1:
        raise SystemExit("FAILED: removal left stale document entries")
    if len(engine._faiss_id_to_uid) != TOTAL_DOCS - 1:
        raise SystemExit("FAILED: removal left stale id entries")

    results = engine.search_index("unique marker 42", k=5)
    paths = [
        engine._documents_map[uid]["file_path"]
        for uid in results
        if uid in engine._documents_map
    ]
    if not paths:
        raise SystemExit("FAILED: search returned no results after concurrency test")
    if not any(path.endswith("doc_42.txt") for path in paths):
        raise SystemExit(f"FAILED: expected doc_42 in results, got {paths}")
    if any(path.endswith("doc_0.txt") for path in paths):
        raise SystemExit("FAILED: removed doc_0 still appears in search results")

    print(
        f"PASS: {TOTAL_DOCS} concurrent adds + removal in {elapsed:.2f}s; "
        f"vectors={engine._index.ntotal}, docs={len(engine._documents_map)}"
    )
    tmp.cleanup()


if __name__ == "__main__":
    main()
