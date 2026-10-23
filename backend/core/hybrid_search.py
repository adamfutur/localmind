from backend.core.vector_store import get_vector_store
from backend.core.embeddings import get_embedding_model
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata
from sqlalchemy.orm import Session
from sqlalchemy import or_


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

    def search(self, query: str, k=10):
        normalized = query.strip()
        if not normalized:
            return []

        # 1. Semantic Search. If no embedding backend is available, keep working
        # with filename/path matches instead of failing the whole request.
        semantic_results = []
        if not self._semantic_disabled:
            try:
                query_embedding = self._embedding().embed_query(query)
                semantic_results = self.vector_store.search(query_embedding, k=k)
            except Exception as exc:
                self._semantic_disabled = True
                print(f"[Search] Semantic search unavailable ({exc}); using keyword search only.")

        # 2. Keyword Search: match any query word against filename or path.
        terms = [term for term in normalized.split() if term] or [normalized]
        filters = []
        for term in terms:
            filters.append(FileMetadata.filename.ilike(f"%{term}%"))
            filters.append(FileMetadata.path.ilike(f"%{term}%"))

        db: Session = SessionLocal()
        try:
            keyword_results = db.query(FileMetadata).filter(
                or_(*filters)
            ).limit(k).all()
            keyword_rows = [
                {"path": row.path, "filename": row.filename}
                for row in keyword_results
            ]
        finally:
            db.close()

        # 3. Merge (semantic first, then keyword matches not already listed)
        final_results = []
        seen_paths = set()

        for res in semantic_results:
            path = res['metadata']['path']
            if path not in seen_paths:
                final_results.append({
                    "type": "semantic",
                    "path": path,
                    "score": res['score'],
                    "content_snippet": res['metadata'].get('text', '')[:200]
                })
                seen_paths.add(path)

        for row in keyword_rows:
            if row['path'] not in seen_paths:
                final_results.append({
                    "type": "keyword",
                    "path": row['path'],
                    "score": 0.0,  # No similarity score for a filename match
                    "content_snippet": f"Filename match: {row['filename']}"
                })
                seen_paths.add(row['path'])

        return final_results[:k]
