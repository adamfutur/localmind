import os
import pickle
import re
import sqlite3
import threading

import faiss
import numpy as np

from backend.config import VECTOR_SAVE_INTERVAL, VECTOR_STORE_PATH

_instance = None
_instance_lock = threading.Lock()

# Tokens keep code-friendly characters (config.py, embed_query, C++), but
# strip sentence punctuation. Common English words are ignored only when the
# query has at least one more specific term.
_TOKEN_RE = re.compile(r"[\w.+#-]+", re.UNICODE)
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can",
    "could", "did", "do", "does", "for", "from", "how", "i", "in", "into",
    "is", "it", "its", "me", "my", "no", "not", "of", "on", "or", "our",
    "over", "should", "that", "the", "their", "these", "they", "this",
    "those", "to", "under", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "yes", "you", "your",
    # French filler words. The embedding model is English-first, and users
    # often search with a French phrase such as "mon cv".
    "le", "la", "les", "un", "une", "des", "du", "de", "dans", "pour",
    "avec", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "leur", "leurs", "sur", "sous", "et",
    "ou", "où", "à", "au", "aux", "ce", "cet", "cette", "ces", "je", "tu",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "est", "sont",
    "être", "avoir", "que", "qui", "quoi", "comment", "quand", "pourquoi",
    "quel", "quelle", "quels", "quelles", "plus", "moins", "très",
})

# Files that are generated, vendored, or low-signal for a code/document
# search. They are down-ranked rather than removed, so searching for a lock
# file by name still works.
_NOISY_PATH_MARKERS = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "cargo.lock", "/node_modules/", "/dist/", "/build/", "/target/",
    "/coverage/", "/.git/", "/.vscode/", "/.kilo/", "/__pycache__/",
    "/glassfish", "__admingui", "/virtual machines/", "/ppsspp/",
)
_SOURCE_EXTENSIONS = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".md", ".markdown", ".rst", ".txt", ".sql", ".sh", ".ps1",
})
_LOW_SIGNAL_EXTENSIONS = frozenset({
    ".html", ".htm", ".css", ".scss", ".less", ".log", ".csv", ".json",
    ".jsonl", ".xml",
})
_LOW_SIGNAL_PATH_MARKERS = (
    "/scripts/benchmark", "/benchmarks/", "/tests/", "/test_",
    "/fixtures/",
)


def query_terms(query: str) -> list[str]:
    """Return meaningful query terms, preserving code-friendly punctuation."""
    terms: list[str] = []
    for match in _TOKEN_RE.findall(query.casefold()):
        term = match.strip('.,;:!?()[]{}"\'')
        if term and re.search(r"\w", term, re.UNICODE) and term not in terms:
            terms.append(term)

    # A query made only of stopwords ("the", "how") has no keyword intent.
    return [term for term in terms if term not in _STOPWORDS]


def is_noisy_path(path: str) -> bool:
    normalized = path.casefold().replace("\\", "/")
    return any(marker in normalized for marker in _NOISY_PATH_MARKERS)


def path_allowed(path: str, query: str) -> bool:
    """Hide vendor/generated paths unless the query mentions them."""
    if not is_noisy_path(path):
        return True

    normalized = path.casefold().replace("\\", "/")
    query_words = set(re.findall(r"[a-z0-9]+", query.casefold()))
    for marker in _NOISY_PATH_MARKERS:
        if marker not in normalized:
            continue
        marker_words = set(re.findall(r"[a-z0-9]+", marker))
        if marker_words & query_words:
            return True
    return False


def _path_quality(path: str) -> float:
    normalized = path.casefold().replace("\\", "/")
    if any(marker in normalized for marker in _NOISY_PATH_MARKERS):
        return -2.0
    if any(marker in normalized for marker in _LOW_SIGNAL_PATH_MARKERS):
        return -0.75

    extension = os.path.splitext(path)[1].lower()
    if extension in _SOURCE_EXTENSIONS:
        return 1.0
    if extension in _LOW_SIGNAL_EXTENSIONS:
        return -0.5
    return 0.0


def _snippet_at(text: str, position: int, width: int = 220) -> str:
    start = max(0, position - 70)
    end = min(len(text), start + width)
    snippet = text[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _term_pattern(term: str):
    """Match a term at the start of a word, not in the middle of one.

    This makes "git" miss "digital" while still matching "local" in
    "LocalMind" and "query" in "embed_query". Requiring a word end would make
    code identifiers and compound words much harder to find.
    """
    left = r"(?<![A-Za-z0-9])" if re.match(r"[A-Za-z0-9]", term) else ""
    return re.compile(left + re.escape(term), re.UNICODE)


class VectorStore:
    """In-process FAISS index with batched, atomic persistence.

    Chunk text is also kept in an in-memory SQLite FTS5 index. FTS5 gives
    sub-millisecond keyword lookup over file contents, while the pickle stays
    the source of truth so the FTS index can be rebuilt on load.
    """

    def __init__(self, dimension=384):  # MiniLM-L6-v2 is 384 dim
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []  # List of dicts matching index
        self._lock = threading.RLock()
        self._pending_saves = 0
        self._keyword_db = None
        self._init_keyword_index()
        self.load()

    def _init_keyword_index(self):
        try:
            self._keyword_db = sqlite3.connect(":memory:", check_same_thread=False)
            self._keyword_db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
                "path UNINDEXED, content, "
                "tokenize=\"unicode61 remove_diacritics 2 tokenchars '_.+#-'\""
                ")"
            )
            self._keyword_db.commit()
        except sqlite3.OperationalError as exc:
            # Very old Python builds may not ship FTS5. Semantic search still
            # works; keyword content search is simply disabled.
            self._keyword_db = None
            print(f"[VectorStore] FTS5 keyword index unavailable: {exc}")

    def _rebuild_keyword_index(self):
        if self._keyword_db is None:
            return

        self._keyword_db.execute("DELETE FROM chunk_fts")
        rows = [
            (item.get("path", ""), item.get("text", ""))
            for item in self.metadata
            if item.get("text")
        ]
        if rows:
            self._keyword_db.executemany(
                "INSERT INTO chunk_fts(path, content) VALUES (?, ?)", rows
            )
        self._keyword_db.commit()

    def add(self, embeddings: list[list[float]], meta: list[dict]):
        if not embeddings:
            return

        with self._lock:
            vectors = np.array(embeddings).astype("float32")
            self.index.add(vectors)
            self.metadata.extend(meta)

            if self._keyword_db is not None:
                rows = [
                    (item.get("path", ""), item.get("text", ""))
                    for item in meta
                    if item.get("text")
                ]
                if rows:
                    self._keyword_db.executemany(
                        "INSERT INTO chunk_fts(path, content) VALUES (?, ?)", rows
                    )
                    self._keyword_db.commit()

            self._pending_saves += len(embeddings)

            if self._pending_saves >= VECTOR_SAVE_INTERVAL:
                self.save()

    def search(self, query_vector: list[float], k=5):
        with self._lock:
            if self.index.ntotal == 0:
                return []

            params = np.array([query_vector]).astype("float32")
            distances, indices = self.index.search(params, k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.metadata):
                    results.append({
                        "score": float(distances[0][i]),
                        "metadata": self.metadata[idx],
                    })
            return results

    def keyword_search(self, query: str, k: int = 10) -> list[dict]:
        """Search chunk text (not filenames) for the query's keywords.

        FTS5 narrows the candidates with prefix matching, then Python reranks
        them so chunks containing every term, exact phrases, and more frequent
        terms come first. Results are deduped by file path.
        """
        terms = query_terms(query)
        if not terms or self._keyword_db is None:
            return []

        # Prefix matching lets "local" find "LocalMind" and "config" find
        # "config.py" without matching the middle of unrelated words.
        match_query = " OR ".join(f'"{term}"*' for term in terms)
        fetch_limit = min(max(k * 25, 250), 1000)
        phrase = " ".join(terms)

        with self._lock:
            try:
                rows = self._keyword_db.execute(
                    "SELECT path, content, bm25(chunk_fts) "
                    "FROM chunk_fts WHERE chunk_fts MATCH ? "
                    "ORDER BY bm25(chunk_fts) LIMIT ?",
                    (match_query, fetch_limit),
                ).fetchall()
            except sqlite3.OperationalError as exc:
                print(f"[VectorStore] Keyword query failed: {exc}")
                return []

            patterns = {term: _term_pattern(term) for term in terms}
            candidates = []

            for path, content, bm25_score in rows:
                if not path or not content:
                    continue

                text_lower = content.casefold()
                matched = []
                positions = []
                for term, pattern in patterns.items():
                    match = pattern.search(text_lower)
                    if match:
                        matched.append(term)
                        positions.append(match.start())

                if not matched:
                    continue

                phrase_match = len(terms) > 1 and phrase in text_lower
                frequency = sum(
                    len(patterns[term].findall(text_lower)) for term in matched
                )
                candidates.append((
                    len(matched) == len(terms),  # all query terms present
                    len(matched),
                    phrase_match,
                    _path_quality(path),
                    -float(bm25_score),  # bm25 is negative; larger is better
                    frequency,
                    -min(positions),  # earlier match first
                    path,
                    content,
                ))

        candidates.sort(key=lambda item: item[:7], reverse=True)

        results = []
        seen_paths = set()
        for _, matched_count, phrase_match, _, _, frequency, negative_position, path, content in candidates:
            if path in seen_paths:
                continue

            results.append({
                "score": float(matched_count + (1 if phrase_match else 0) + frequency / 10),
                "metadata": {"path": path, "text": content},
                "snippet": _snippet_at(content, -negative_position),
                "matched_terms": matched_count,
                "all_terms": matched_count == len(terms),
            })
            seen_paths.add(path)

            if len(results) >= k:
                break

        return results

    def stats(self) -> dict:
        with self._lock:
            return {
                "vectors": int(self.index.ntotal),
                "vector_metadata": len(self.metadata),
            }

    def save(self):
        with self._lock:
            index_tmp = str(VECTOR_STORE_PATH) + ".tmp"
            meta_tmp = str(VECTOR_STORE_PATH) + ".meta.tmp"

            faiss.write_index(self.index, index_tmp)
            with open(meta_tmp, "wb") as f:
                pickle.dump(self.metadata, f, protocol=pickle.HIGHEST_PROTOCOL)

            os.replace(index_tmp, VECTOR_STORE_PATH)
            os.replace(meta_tmp, str(VECTOR_STORE_PATH) + ".meta")
            self._pending_saves = 0

    def load(self):
        with self._lock:
            if not os.path.exists(VECTOR_STORE_PATH):
                self.metadata = []
                self._rebuild_keyword_index()
                return

            self.index = faiss.read_index(str(VECTOR_STORE_PATH))
            meta_path = str(VECTOR_STORE_PATH) + ".meta"
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    self.metadata = pickle.load(f)
            else:
                self.metadata = []

            self._rebuild_keyword_index()


def get_vector_store() -> VectorStore:
    """Return the single shared index used by indexing and search."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = VectorStore()
    return _instance
