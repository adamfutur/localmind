"""Keyword search must match chunk contents, not filenames or substrings."""

import backend.core.vector_store as vector_store_module
from backend.core.vector_store import VectorStore


def test_keyword_search_matches_content(tmp_path, monkeypatch):
    monkeypatch.setattr(
        vector_store_module,
        "VECTOR_STORE_PATH",
        tmp_path / "vectors.faiss",
    )

    store = VectorStore(dimension=8)
    store.add(
        [[0.0] * 8 for _ in range(7)],
        [
            {
                "path": "C:/notes/embeddings.py",
                "text": "def embed_query(query): return query",
            },
            {
                "path": "C:/notes/digital.txt",
                "text": "digital marketing notes with no code",
            },
            {
                "path": "C:/notes/git.txt",
                "text": "run git status then git commit",
            },
            {
                "path": "C:/notes/localmind.md",
                "text": "The LocalMind application searches local files.",
            },
            {
                "path": "C:/notes/borrow.md",
                "text": "The borrow checker rejects aliased mutable references.",
            },
            {
                "path": "C:/notes/config.md",
                "text": "Set config.py values before starting.",
            },
            {
                "path": "C:/notes/embeddings.py",
                "text": "Second chunk for embed_query with a query cache.",
            },
        ],
    )

    def paths(query):
        return [
            result["metadata"]["path"]
            for result in store.keyword_search(query, k=10)
        ]

    assert "C:/notes/embeddings.py" in paths("embed_query")
    assert "C:/notes/git.txt" in paths("git")
    assert "C:/notes/localmind.md" in paths("local")
    assert "C:/notes/borrow.md" in paths("borrow checker")
    assert "C:/notes/config.md" in paths("config.py")

    # A prefix match must not match the middle of an unrelated word.
    assert "C:/notes/digital.txt" not in paths("git")

    # A typo with no content match must not return arbitrary chunks.
    assert paths("loclmind") == []

    # Multiple chunks from the same file are deduplicated by path.
    deduped = paths("embed_query")
    assert deduped.count("C:/notes/embeddings.py") == 1
