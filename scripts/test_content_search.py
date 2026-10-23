"""Regression test for keyword search over chunk text (not filenames)."""
import tempfile
from pathlib import Path

import backend.config as config


def main():
    tmp = tempfile.TemporaryDirectory()
    config.VECTOR_STORE_PATH = Path(tmp.name) / "vectors.faiss"

    from backend.core.vector_store import VectorStore

    store = VectorStore()
    store.add(
        [[0.0] * store.dimension for _ in range(7)],
        [
            {"path": "C:/notes/embeddings.py", "text": "def embed_query(query): return query"},
            {"path": "C:/notes/digital.txt", "text": "digital marketing notes with no code"},
            {"path": "C:/notes/git.txt", "text": "run git status then git commit"},
            {"path": "C:/notes/localmind.md", "text": "The LocalMind application searches local files."},
            {"path": "C:/notes/borrow.md", "text": "The borrow checker rejects aliased mutable references."},
            {"path": "C:/notes/config.md", "text": "Set config.py values before starting."},
            {"path": "C:/notes/embeddings.py", "text": "Second chunk for embed_query with a query cache."},
        ],
    )

    def paths(query):
        return [result["metadata"]["path"] for result in store.keyword_search(query, k=10)]

    checks = {
        "embed_query": "C:/notes/embeddings.py",
        "git": "C:/notes/git.txt",
        "local": "C:/notes/localmind.md",
        "borrow checker": "C:/notes/borrow.md",
        "config.py": "C:/notes/config.md",
    }

    for query, expected in checks.items():
        found = paths(query)
        if expected not in found:
            raise SystemExit(f"FAILED: {query!r} did not find {expected}; got {found}")

    if "C:/notes/digital.txt" in paths("git"):
        raise SystemExit("FAILED: 'git' matched the middle of 'digital'")

    if paths("loclmind"):
        raise SystemExit("FAILED: typo query unexpectedly matched keyword content")

    deduped = paths("embed_query")
    if deduped.count("C:/notes/embeddings.py") != 1:
        raise SystemExit(f"FAILED: results were not deduped by path: {deduped}")

    print("PASS: content keyword search (FTS5, prefix matching, phrase ranking, dedupe)")
    tmp.cleanup()


if __name__ == "__main__":
    main()
