import numpy as np
import faiss
from fastembed import TextEmbedding
import os
import json
from threading import Lock

# Configuration for the embedding model and FAISS index
MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIM = 384 # Dimension for BAAI/bge-small-en-v1.5
FAISS_INDEX_PATH = "data/faiss_index.bin"
DOCUMENTS_MAP_PATH = "data/documents_map.json"

# Initialize the embedding model (this might download on first run)
print(f"[Engine] Initializing TextEmbedding model: {MODEL_NAME}...")
_model = TextEmbedding(model_name=MODEL_NAME)
print(f"[Engine] TextEmbedding model loaded.")

# Initialize FAISS index and a dictionary to map unique_id to content
_index = faiss.IndexFlatL2(DIM)
# documents_map: {unique_chunk_id: {"file_path": ..., "content": "..."}}
_documents_map = {} 
_index_lock = Lock() # To ensure thread-safe access to FAISS index and documents_map

def _save_index_and_documents():
    """Saves the FAISS index and the documents map to disk."""
    with _index_lock:
        # Save FAISS index
        faiss.write_index(_index, FAISS_INDEX_PATH)
        # Save documents map
        with open(DOCUMENTS_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(_documents_map, f, ensure_ascii=False, indent=2)
    print(f"[Engine] FAISS index and document map saved to {FAISS_INDEX_PATH} and {DOCUMENTS_MAP_PATH}")

def load_index_and_documents():
    """Loads the FAISS index and the documents map from disk."""
    global _index, _documents_map
    with _index_lock:
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCUMENTS_MAP_PATH):
            try:
                _index = faiss.read_index(FAISS_INDEX_PATH)
                with open(DOCUMENTS_MAP_PATH, "r", encoding="utf-8") as f:
                    _documents_map = json.load(f)
                print(f"[Engine] FAISS index and document map loaded. {_index.ntotal} vectors indexed.")
            except Exception as e:
                print(f"[Engine] Error loading FAISS index or documents map: {e}. Starting with empty index.")
                _index = faiss.IndexFlatL2(DIM)
                _documents_map = {}
        else:
            print("[Engine] No existing FAISS index or document map found. Starting with empty index.")
            _index = faiss.IndexFlatL2(DIM)
            _documents_map = {}

def add_document_to_index(content: str, unique_id: str, file_path: str = None):
    """
    Adds a document (or chunk) to the FAISS index and updates the documents map.
    unique_id is typically "file_path::chunk::idx"
    """
    with _index_lock:
        # Check if the unique_id already exists and remove its old vector if so
        if unique_id in _documents_map:
            # This is a simplification. FAISS.remove() is for specific vector IDs.
            # For `IndexFlatL2`, removing by arbitrary unique_id requires rebuilding or
            # more complex indexing. For now, we'll just overwrite in _documents_map
            # and accept potential "stale" vectors in FAISS if not re-added in same position.
            # A more robust solution for deletes/updates might involve re-indexing segments
            # or using a more advanced FAISS index type.
            print(f"[Engine] Warning: {unique_id} already exists. Overwriting in map. Index might have stale vector if not aligned.")
            # For true removal in IndexFlatL2, you would need to know the exact internal FAISS ID (if any)
            # and potentially rebuild or use a filtering mechanism.
            # For simplicity here, we'll ensure `add` logic works for new items.
            pass # Keep it simple for adding, assume scanner cleans up old chunks

        vec = list(_model.embed([content]))[0]
        vec = np.array(vec, dtype="float32").reshape(1, -1)
        _index.add(vec)
        
        # Store content and original file_path with the unique_id
        _documents_map[unique_id] = {"file_path": file_path if file_path else unique_id.split("::chunk::")[0], "content": content, "faiss_id": _index.ntotal -1} # Store FAISS internal ID
        
        # Periodically save to disk to prevent data loss on crash
        if _index.ntotal % 100 == 0: # Save every 100 additions
            _save_index_and_documents()
        
    # print(f"[Engine] Added document {unique_id}. Total vectors: {_index.ntotal}")


def remove_document_from_index_by_file_path(original_file_path: str):
    """
    Removes all chunks associated with a given original file path from the FAISS index and documents map.
    Note: FAISS IndexFlatL2 doesn't have an easy way to delete vectors by custom ID.
    This implementation involves creating a new index without the removed items.
    This can be slow for very large indexes and should ideally be optimized with more advanced FAISS features or by batching.
    """
    with _index_lock:
        if _index.ntotal == 0:
            return

        # Find all unique_chunk_ids associated with the file_path
        chunk_ids_to_remove = [
            uid for uid, doc_info in _documents_map.items() 
            if doc_info["file_path"] == original_file_path
        ]

        if not chunk_ids_to_remove:
            # print(f"[Engine] No chunks found for file path: {original_file_path}")
            return

        print(f"[Engine] Removing {len(chunk_ids_to_remove)} chunks for file: {original_file_path}")

        # Create new index and document map excluding the removed chunks
        new_index = faiss.IndexFlatL2(DIM)
        new_documents_map = {}
        
        vectors_to_add = []
        new_uid_map_for_faiss_id = {} # map new faiss id to unique_id

        current_faiss_id = 0
        for uid, doc_info in _documents_map.items():
            if uid not in chunk_ids_to_remove:
                # Retrieve the vector from the old index if needed, or re-embed if not possible
                # For IndexFlatL2, we cannot retrieve by uid or remove efficiently.
                # The simplest is to rebuild the index from content.
                # A more optimized way would be to use a Faiss Index with IDs (e.g., IndexIDMap)
                # or a numpy array and filter directly.
                
                # For now, we'll re-embed for simplicity. This is inefficient for large datasets.
                # If content is always stored, we can re-embed.
                content = doc_info['content']
                new_vec = list(_model.embed([content]))[0]
                vectors_to_add.append(new_vec)
                new_documents_map[uid] = {"file_path": doc_info["file_path"], "content": content, "faiss_id": current_faiss_id}
                current_faiss_id += 1
                
        if vectors_to_add:
            new_index.add(np.array(vectors_to_add, dtype="float32"))
        
        _index = new_index
        _documents_map = new_documents_map
        _save_index_and_documents() # Save the rebuilt index and map
        print(f"[Engine] Successfully removed chunks for {original_file_path}. New total vectors: {_index.ntotal}")


def search_index(query: str, k: int = 5) -> list[str]:
    """
    Performs a semantic search for the given query and returns the unique_chunk_ids of the top k results.
    """
    with _index_lock:
        if _index.ntotal == 0:
            return ["⚠️ No files indexed yet. Please run /index first."]

        query_vec = list(_model.embed([query]))[0]
        query_vec = np.array(query_vec, dtype="float32").reshape(1, -1)

        # Ensure k is not greater than the number of indexed items
        k_actual = min(k, _index.ntotal)
        if k_actual == 0:
            return ["⚠️ No files indexed yet. Please run /index first."]

        D, I = _index.search(query_vec, k_actual) # D are distances, I are internal FAISS IDs

        results_unique_ids = []
        for faiss_id in I[0]:
            # Find the unique_id associated with this internal FAISS ID
            # This is inefficient lookup. A better way is to have a direct map from FAISS ID to unique_id.
            # After rebuilding the index, faiss_id in _documents_map will be correctly mapped.
            found_uid = next((uid for uid, doc_info in _documents_map.items() if doc_info.get("faiss_id") == faiss_id), None)
            if found_uid:
                results_unique_ids.append(found_uid)
        
        # print(f"[Engine] Search results for '{query}': {results_unique_ids}")
        return results_unique_ids

def get_document_content_by_id(unique_id: str) -> str | None:
    """Retrieves the content of a specific chunk/document by its unique ID."""
    with _index_lock:
        doc_info = _documents_map.get(unique_id)
        if doc_info:
            return doc_info.get("content")
        return None

# Initial load when module is imported
load_index_and_documents()