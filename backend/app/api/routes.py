import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.app.indexing.scanner import scan_folder, index_single_file
from backend.app.search.query import semantic_search_results
from backend.app.llm.qa import answer_question
from backend.app.storage.metadata import get_all_indexed_files_metadata

router = APIRouter(prefix="/api", tags=["LocalMind API"]) # Added prefix and tags for OpenAPI UI

@router.post("/index", summary="Index Folder")
async def index_directory_endpoint(path: str, background_tasks: BackgroundTasks):
    """
    Initiates a background task to scan and index all relevant files within the specified directory.
    """
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Provided path is not a valid directory: {path}")
    
    background_tasks.add_task(scan_folder, path)
    return {"message": f"Indexing of directory '{path}' started in the background."}

@router.post("/index-file", summary="Index Single File")
async def index_file_endpoint(path: str, background_tasks: BackgroundTasks):
    """
    Initiates a background task to index a single specified file.
    """
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail=f"Provided path is not a valid file: {path}")
    
    background_tasks.add_task(index_single_file, path)
    return {"message": f"Indexing of file '{path}' started in the background."}


@router.get("/search", summary="Semantic Search")
async def search_endpoint(q: str, k: int = 5):
    """
    Performs a semantic search against the indexed content for the given query.
    Returns a list of relevant document paths (or unique chunk IDs if chunked).
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query 'q' cannot be empty.")
    
    results = semantic_search_results(q, k)
    return {"query": q, "results": results}


@router.get("/ask", summary="Ask Question to LLM")
async def ask_endpoint(q: str, k: int = 3):
    """
    Asks a question to the local LLM, providing relevant indexed content as context.
    Returns the LLM's generated answer.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Question 'q' cannot be empty.")
        
    response = await answer_question(q, k) # Await if answer_question is async
    return {"question": q, "answer": response}

@router.get("/indexed-files", summary="Get Indexed Files Metadata")
async def get_indexed_files_metadata_endpoint():
    """
    Retrieves metadata for all files currently tracked in the system.
    """
    files_metadata = get_all_indexed_files_metadata()
    return {"files": files_metadata}

@router.get("/get-file-content", summary="Get File Content by ID")
async def get_file_content_endpoint(unique_id: str):
    """
    Retrieves the content of a specific chunk or file identified by its unique ID.
    Used for providing context to the LLM or displaying full content.
    """
    from backend.app.search.engine import get_document_content_by_id
    content = get_document_content_by_id(unique_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content for ID '{unique_id}' not found.")
    return {"id": unique_id, "content": content}