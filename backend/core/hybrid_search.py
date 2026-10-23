import os
import re

from backend.config import SEMANTIC_MAX_DISTANCE, SEMANTIC_RELATIVE_MARGIN
from backend.core.embeddings import get_embedding_model
from backend.core.vector_store import (
    get_vector_store,
    path_allowed,
    query_terms,
)
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata
from sqlalchemy import or_
from sqlalchemy.orm import Session

# Reciprocal-rank fusion constant. Keyword hits get a slight boost because
# exact keyword matches are usually what the user means when they type terms.
RRF_K = 60
KEYWORD_WEIGHT = 1.25
SEMANTIC_QUALITY_WEIGHT = 0.5

# A single word or a code-like token is a keyword lookup. Everything else is
# treated as a natural-language question where semantic search is stronger.
_CODE_LIKE_RE = re.compile(r"[_./\\:#+()\[\]{}]|[a-z][A-Z]|\d")

_CV_TERMS = frozenset({"cv", "resume", "résumé", "curriculum", "vitae"})
_CV_ALIASES = ("cv", "resume", "résumé", "curriculum", "vitae")
_DOCUMENT_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".doc", ".odt", ".rtf",
})
_EXTENSION_NAMES = {
    "pdf": ".pdf",
    "docx": ".docx",
    "doc": ".doc",
    "odt": ".odt",
    "rtf": ".rtf",
}


def _looks_like_keyword_query(query: str) -> bool:
    if len(query.split()) == 1:
        return True
    return bool(_CODE_LIKE_RE.search(query))


def _path_extension(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _token_in_text(term: str, text: str) -> bool:
    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
            text,
            re.IGNORECASE,
        )
    )


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _has_cv_alias(path: str) -> bool:
    lower = path.casefold()
    return any(
        re.search(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            lower,
        )
        for alias in _CV_ALIASES
    )


def _looks_like_cv_result(result) -> bool:
    if _has_cv_alias(result.get("path", "")):
        return True
    snippet = (result.get("content_snippet") or "").casefold()
    return "curriculum vitae" in snippet or "resume" in snippet


class HybridSearch:
    def __init__(self):
        # Cheap to construct: the embedding model is loaded on first use.
        self.vector_store = get_vector_store()
        self._embedding_model = None
        self._semantic_disabled = False

    def _embedding(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    @staticmethod
    def _filter_semantic(results):
        """Drop weak semantic hits that are far from the best match.

        all-MiniLM distances are roughly 0 (identical) to 2 (unrelated).
        Without a gate, a query with no real match still returns random
        snippets, which looks like a broken search.
        """
        if not results:
            return []

        best = min(float(result["score"]) for result in results)
        limit = min(
            float(SEMANTIC_MAX_DISTANCE),
            best + float(SEMANTIC_RELATIVE_MARGIN),
        )
        return [result for result in results if float(result["score"]) <= limit]

    @staticmethod
    def _keyword_first_results(keyword_results, semantic_results, k):
        """Return exact content matches and omit semantic-only noise."""
        semantic_by_path = {}
        for result in semantic_results:
            path = result.get("metadata", {}).get("path")
            if path and path not in semantic_by_path:
                semantic_by_path[path] = result

        final_results = []
        for result in keyword_results:
            path = result.get("metadata", {}).get("path")
            if not path:
                continue

            semantic = semantic_by_path.get(path)
            final_results.append({
                "type": "semantic+keyword" if semantic else "keyword",
                "path": path,
                "score": float(semantic["score"]) if semantic else 0.0,
                "content_snippet": (
                    result.get("snippet")
                    or result["metadata"].get("text", "")[:200]
                ),
            })

            if len(final_results) >= k:
                break

        return final_results

    @staticmethod
    def _merge_results(first, second, k):
        merged = []
        seen = set()
        for result in list(first) + list(second):
            path = result.get("path")
            if not path or path in seen:
                continue
            merged.append(result)
            seen.add(path)
            if len(merged) >= k:
                break
        return merged

    def _content_results(self, semantic_results, keyword_results, k, keyword_mode):
        if keyword_mode and keyword_results:
            return self._keyword_first_results(keyword_results, semantic_results, k)

        # Natural-language queries: partial keyword hits are usually noise
        # when semantic results already exist. Keep all-term matches (strong
        # keyword evidence) and ignore partial ones.
        strong_keyword_results = [
            result for result in keyword_results if result.get("all_terms")
        ]
        if strong_keyword_results:
            keyword_results = strong_keyword_results
        elif semantic_results:
            keyword_results = []

        return self._fuse(semantic_results, keyword_results, k)

    def _filename_results(self, query: str, k: int, document_intent: bool):
        """Find files by name/path. This is what makes "mon cv" useful.

        Filename search is intentionally document-aware: a CV named
        ``cv_Adam.pdf`` outranks an unrelated source file that merely contains
        the letters "cv".
        """
        terms = query_terms(query)
        if not terms:
            return []

        # File-type words are filters, not filename text. Otherwise
        # "mon cv pdf" would match every PDF on the machine.
        mentioned_extensions = {
            _EXTENSION_NAMES[term] for term in terms if term in _EXTENSION_NAMES
        }
        text_terms = [term for term in terms if term not in _EXTENSION_NAMES]
        cv_intent = any(term in _CV_TERMS for term in text_terms)

        search_terms = list(text_terms)
        if cv_intent:
            for alias in _CV_ALIASES:
                if alias not in search_terms:
                    search_terms.append(alias)

        db: Session = SessionLocal()
        try:
            query_obj = db.query(FileMetadata)
            if document_intent:
                query_obj = query_obj.filter(
                    FileMetadata.extension.in_(_DOCUMENT_EXTENSIONS)
                )
            if mentioned_extensions:
                query_obj = query_obj.filter(
                    FileMetadata.extension.in_(mentioned_extensions)
                )

            filters = []
            for term in search_terms:
                pattern = _like_pattern(term)
                filters.append(
                    FileMetadata.filename.ilike(pattern, escape="\\")
                )
                filters.append(
                    FileMetadata.path.ilike(pattern, escape="\\")
                )

            if filters:
                query_obj = query_obj.filter(or_(*filters))
            rows = query_obj.limit(400).all()
            rows = [
                (row.filename, row.path, row.extension, row.modified_at)
                for row in rows
            ]
        finally:
            db.close()

        scored = []
        for filename, path, extension, modified_at in rows:
            if not path or not path_allowed(path, query):
                continue

            name = (filename or "").casefold()
            lower_path = path.casefold()
            extension = (extension or "").casefold()

            matched_terms = sum(
                1 for term in text_terms if term in name or term in lower_path
            )
            exact_terms = sum(
                1 for term in text_terms if _token_in_text(term, name)
            )
            cv_alias = _has_cv_alias(path)
            is_document = extension in _DOCUMENT_EXTENSIONS

            # A CV query must not return an unrelated "data scientist"
            # document merely because that phrase was in the query.
            if cv_intent and not cv_alias:
                continue

            score = matched_terms * 10 + exact_terms * 6
            if is_document:
                score += 20
            if cv_intent and cv_alias and is_document:
                score += 20
            if mentioned_extensions and extension in mentioned_extensions:
                score += 15

            modified_timestamp = (
                modified_at.timestamp() if modified_at is not None else 0.0
            )
            scored.append((score, modified_timestamp, path, filename))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return [
            {
                "type": "filename",
                "path": path,
                "score": 0.0,
                "content_snippet": f"Filename match: {filename}",
            }
            for _, _, path, filename in scored[:k]
        ]

    def search(self, query: str, k=10):
        normalized = query.strip()
        if not normalized:
            return []

        k = max(1, int(k))
        terms = query_terms(normalized)
        if not terms:
            # Query was only stopwords ("the", "how"); there is nothing useful
            # to match and semantic search would return random nearby chunks.
            return []

        keyword_mode = _looks_like_keyword_query(normalized)
        document_intent = bool(set(terms) & _CV_TERMS) or any(
            term in _EXTENSION_NAMES for term in terms
        )
        cv_intent = any(term in _CV_TERMS for term in terms)

        # Semantic search. If no embedding backend is available, keep working
        # with content keywords instead of failing the whole request.
        semantic_results = []
        if not self._semantic_disabled:
            try:
                query_embedding = self._embedding().embed_query(normalized)
                semantic_results = self.vector_store.search(query_embedding, k=k)
            except Exception as exc:
                self._semantic_disabled = True
                print(f"[Search] Semantic search unavailable ({exc}); using content keywords only.")

        semantic_results = self._filter_semantic(semantic_results)

        keyword_results = []
        try:
            keyword_results = self.vector_store.keyword_search(normalized, k=k)
        except Exception as exc:
            print(f"[Search] Content keyword search unavailable ({exc}); using semantic results only.")

        # Hide vendor/generated trees and benchmark fixtures unless the user
        # explicitly asks for them.
        semantic_results = [
            result for result in semantic_results
            if path_allowed(result.get("metadata", {}).get("path", ""), normalized)
        ]
        keyword_results = [
            result for result in keyword_results
            if path_allowed(result.get("metadata", {}).get("path", ""), normalized)
        ]

        if document_intent:
            # "mon cv", "resume", "pdf", "docx" should return documents, not
            # random code chunks that happen to be semantically nearby.
            extensions = {
                _EXTENSION_NAMES[term]
                for term in terms
                if term in _EXTENSION_NAMES
            } or _DOCUMENT_EXTENSIONS

            filename_results = self._filename_results(
                normalized, k, document_intent=True
            )
            filename_results = [
                result for result in filename_results
                if _path_extension(result["path"]) in extensions
            ]

            content_results = self._content_results(
                semantic_results, keyword_results, k, keyword_mode
            )
            content_results = [
                result for result in content_results
                if _path_extension(result["path"]) in extensions
            ]
            if cv_intent:
                content_results = [
                    result for result in content_results
                    if _looks_like_cv_result(result)
                ]

            merged = self._merge_results(filename_results, content_results, k)
            if merged:
                return merged

            # Do not fall back to unrelated code when the user asked for a
            # document type and no matching document exists.
            return []

        content_results = self._content_results(
            semantic_results, keyword_results, k, keyword_mode
        )
        if content_results:
            return content_results

        # Filename fallback only when content search found nothing.
        return self._filename_results(normalized, k, document_intent=False)

    def _fuse(self, semantic_results, keyword_results, k):
        """Reciprocal-rank fusion of semantic and strong keyword matches."""
        candidates = {}

        def add_candidate(result, source, rank):
            path = result.get("metadata", {}).get("path")
            if not path:
                return
            candidate = candidates.setdefault(path, {"path": path})
            current = candidate.get(source)
            if current is None or rank < current["rank"]:
                candidate[source] = {"rank": rank, "result": result}

        for rank, result in enumerate(semantic_results):
            add_candidate(result, "semantic", rank)
        for rank, result in enumerate(keyword_results):
            add_candidate(result, "keyword", rank)

        for candidate in candidates.values():
            fusion = 0.0
            if "semantic" in candidate:
                fusion += 1.0 / (RRF_K + candidate["semantic"]["rank"])
                semantic_score = float(candidate["semantic"]["result"]["score"])
                quality = max(
                    0.0,
                    1.0 - semantic_score / max(float(SEMANTIC_MAX_DISTANCE), 1e-6),
                )
                fusion += SEMANTIC_QUALITY_WEIGHT * quality
            if "keyword" in candidate:
                fusion += KEYWORD_WEIGHT / (RRF_K + candidate["keyword"]["rank"])
            candidate["fusion"] = fusion

        ordered = sorted(
            candidates.values(),
            key=lambda item: (-item["fusion"], item["path"]),
        )

        final_results = []
        for candidate in ordered[:k]:
            semantic = candidate.get("semantic")
            keyword = candidate.get("keyword")

            if keyword:
                snippet = (
                    keyword["result"].get("snippet")
                    or keyword["result"]["metadata"].get("text", "")[:200]
                )
                result_type = "semantic+keyword" if semantic else "keyword"
                score = float(semantic["result"]["score"]) if semantic else 0.0
            else:
                snippet = semantic["result"]["metadata"].get("text", "")[:200]
                result_type = "semantic"
                score = float(semantic["result"]["score"])

            final_results.append({
                "type": result_type,
                "path": candidate["path"],
                "score": score,
                "content_snippet": snippet,
            })

        return final_results
