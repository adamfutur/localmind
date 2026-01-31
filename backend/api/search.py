from fastapi import APIRouter, Query
from backend.core.hybrid_search import HybridSearch
from pydantic import BaseModel
from typing import List, Optional
from backend.core.vector_store import VectorStore
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata

router = APIRouter()
search_engine = HybridSearch()

class SearchResult(BaseModel):
    type: str
    path: str
    score: float
    content_snippet: str

@router.get("/search", response_model=List[SearchResult])
async def search(q: str = Query(..., min_length=1), limit: int = 10):
    results = search_engine.search(q, k=limit)
    return results

@router.get("/search-status")
async def search_status():
    vs = VectorStore()
    vector_count = int(vs.index.ntotal)
    meta_count = len(vs.metadata)

    s = SessionLocal()
    try:
        files_count = s.query(FileMetadata).count()
    finally:
        s.close()

    return {
        "vectors": vector_count,
        "vector_metadata": meta_count,
        "files": files_count
    }