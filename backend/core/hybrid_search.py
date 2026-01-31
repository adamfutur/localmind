from backend.core.vector_store import VectorStore
from backend.core.embeddings import EmbeddingModel
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata
from sqlalchemy.orm import Session
from sqlalchemy import or_

class HybridSearch:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_model = EmbeddingModel()

    def search(self, query: str, k=10):
        # 1. Semantic Search
        query_embedding = self.embedding_model.embed_query(query)
        semantic_results = self.vector_store.search(query_embedding, k=k)
        
        # 2. Keyword Search (enhanced): match on filename OR path fragments
        db: Session = SessionLocal()
        normalized = query.strip()
        keyword_results = db.query(FileMetadata).filter(
            or_(
                FileMetadata.filename.ilike(f"%{normalized}%"),
                FileMetadata.path.ilike(f"%{normalized}%")
            )
        ).limit(k).all()
        db.close()

        # 3. Merge Strategies (Simple concatenation for now)
        # Ideally we would re-rank or normalize scores
        
        final_results = []
        seen_paths = set()

        # Add semantic results first
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

        # Add keyword results
        for res in keyword_results:
            if res.path not in seen_paths:
                final_results.append({
                    "type": "keyword",
                    "path": res.path,
                    "score": 0.0, # Placeholder
                    "content_snippet": f"Filename match: {res.filename}"
                })
                seen_paths.add(res.path)

        return final_results[:k]
