from backend.app.search.engine import search_index

def semantic_search_results(query: str, k: int = 5) -> list[str]:
    """
    Performs a semantic search and returns a list of unique_chunk_ids.
    """
    return search_index(query, k)