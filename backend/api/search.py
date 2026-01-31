from fastapi import APIRouter, Query
from backend.core.hybrid_search import HybridSearch
from pydantic import BaseModel
from typing import List, Optional

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
