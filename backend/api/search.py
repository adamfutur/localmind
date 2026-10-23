import threading

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.core.hybrid_search import HybridSearch
from backend.core.vector_store import get_vector_store
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata

router = APIRouter()

# Load the embedding model only when search is first used, not at startup.
_search_engine = None
_search_engine_lock = threading.Lock()


def get_search_engine() -> HybridSearch:
    global _search_engine
    if _search_engine is None:
        with _search_engine_lock:
            if _search_engine is None:
                _search_engine = HybridSearch()
    return _search_engine

class SearchResult(BaseModel):
    type: str
    path: str
    score: float
    content_snippet: str

@router.get("/search", response_model=list[SearchResult])
async def search(q: str = Query(..., min_length=1), limit: int = 10):
    results = get_search_engine().search(q, k=limit)
    return results

@router.get("/search-status")
async def search_status():
    stats = get_vector_store().stats()
    vector_count = stats["vectors"]
    meta_count = stats["vector_metadata"]

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