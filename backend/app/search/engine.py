import json
import os
from collections import OrderedDict
from threading import Lock, RLock

import faiss
import numpy as np
from fastembed import TextEmbedding

# Configuration for the embedding model and FAISS index
MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIM = 384  # Dimension for BAAI/bge-small-en-v1.5
FAISS_INDEX_PATH = os.getenv("LOCALMIND_FAISS_INDEX_PATH", "data/faiss_index.bin")
DOCUMENTS_MAP_PATH = os.getenv("LOCALMIND_DOCUMENTS_MAP_PATH", "data/documents_map.json")
QUERY_CACHE_SIZE = int(os.getenv("LOCALMIND_QUERY_CACHE_SIZE", "256"))

# Initialize the embedding model (this might download on first run)
print(f"[Engine] Initializing TextEmbedding model: {MODEL_NAME}...")
_model = TextEmbedding(model_name=MODEL_NAME)
print("[Engine] TextEmbedding model loaded.")

# Initialize FAISS index and a dictionary to map unique_id to content
_index = faiss.IndexFlatL2(DIM)
# documents_map: {unique_chunk_id: {"file_path": ..., "content": ..., "faiss_id": ...}}
_documents_map = {}
# Direct FAISS id -> unique_id lookup, so search does not scan documents_map.
_faiss_id_to_uid = {}

# RLock: add/remove call the save helper while already holding this lock.
_index_lock = RLock()
_model_lock = Lock()
_query_cache = OrderedDict()  # bounded LRU: query -> tuple[float, ...]
_query_cache_lock = Lock()


def _embed_documents(texts: list[str]) -> list[list[float]]:
    with _model_lock:
        return list(_model.embed(texts, batch_size=32))


def _embed_query(query: str) -> tuple[float, ...]:
    """Return a cached query vector, computing it at most once per query."""
    key = query.strip()

    with _query_cache_lock:
        cached = _query_cache.get(key)
        if cached is not None:
            _query_cache.move_to_end(key)
            return cached

    vector = tuple(float(value) for value in _embed_documents([key])[0])

    with _query_cache_lock:
        _query_cache[key] = vector
        _query_cache.move_to_end(key)
        while len(_query_cache) > QUERY_CACHE_SIZE:
            _query_cache.popitem(last=False)

    return vector


def clear_query_cache():
    with _query_cache_lock:
        _query_cache.clear()


def _rebuild_faiss_id_map():
    """Rebuild the direct lookup table. Caller must hold _index_lock."""
    _faiss_id_to_uid.clear()
    for uid, info in _documents_map.items():
        faiss_id = info.get("faiss_id")
        if faiss_id is not None:
            _faiss_id_to_uid[int(faiss_id)] = uid


def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _save_index_and_documents():
    """Saves the FAISS index and the documents map to disk."""
    with _index_lock:
        _ensure_parent(FAISS_INDEX_PATH)
        _ensure_parent(DOCUMENTS_MAP_PATH)

        index_tmp = FAISS_INDEX_PATH + ".tmp"
        map_tmp = DOCUMENTS_MAP_PATH + ".tmp"

        faiss.write_index(_index, index_tmp)
        with open(map_tmp, "w", encoding="utf-8") as f:
            json.dump(_documents_map, f, ensure_ascii=False, indent=2)

        os.replace(index_tmp, FAISS_INDEX_PATH)
        os.replace(map_tmp, DOCUMENTS_MAP_PATH)
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
                _rebuild_faiss_id_map()
                print(f"[Engine] FAISS index and document map loaded. {_index.ntotal} vectors indexed.")
            except Exception as e:
                print(f"[Engine] Error loading FAISS index or documents map: {e}. Starting with empty index.")
                _index = faiss.IndexFlatL2(DIM)
                _documents_map = {}
                _faiss_id_to_uid.clear()
        else:
            print("[Engine] No existing FAISS index or document map found. Starting with empty index.")
            _index = faiss.IndexFlatL2(DIM)
            _documents_map = {}
            _faiss_id_to_uid.clear()


def add_document_to_index(content: str, unique_id: str, file_path: str = None):
    """
    Adds a document (or chunk) to the FAISS index and updates the documents map.
    unique_id is typically "file_path::chunk::idx"
    """
    # Embed outside the index lock so searches can run while a document is prepared.
    vector = _embed_documents([content])[0]

    with _index_lock:
        if unique_id in _documents_map:
            # For IndexFlatL2, removing by arbitrary unique_id requires rebuilding.
            # Keep the old vector and overwrite the map entry; callers should treat
            # unique_id as stable for a given file/chunk.
            print(f"[Engine] Warning: {unique_id} already exists. Overwriting in map. Index might have stale vector if not aligned.")

        vec = np.array(vector, dtype="float32").reshape(1, -1)
        _index.add(vec)

        faiss_id = int(_index.ntotal - 1)
        _documents_map[unique_id] = {
            "file_path": file_path if file_path else unique_id.split("::chunk::")[0],
            "content": content,
            "faiss_id": faiss_id,
        }
        _faiss_id_to_uid[faiss_id] = unique_id

        # Periodically save to disk to prevent data loss on crash
        if _index.ntotal % 100 == 0:  # Save every 100 additions
            _save_index_and_documents()


def remove_document_from_index_by_file_path(original_file_path: str):
    """
    Removes all chunks associated with a given original file path from the FAISS index and documents map.
    Note: FAISS IndexFlatL2 doesn't have an easy way to delete vectors by custom ID.
    This implementation involves creating a new index without the removed items.
    This can be slow for very large indexes and should ideally be optimized with more advanced FAISS features or by batching.
    """
    global _index, _documents_map, _faiss_id_to_uid
    with _index_lock:
        if _index.ntotal == 0:
            return

        # Find all unique_chunk_ids associated with the file_path
        chunk_ids_to_remove = [
            uid for uid, doc_info in _documents_map.items()
            if doc_info["file_path"] == original_file_path
        ]

        if not chunk_ids_to_remove:
            return

        print(f"[Engine] Removing {len(chunk_ids_to_remove)} chunks for file: {original_file_path}")

        kept = [
            (uid, doc_info) for uid, doc_info in _documents_map.items()
            if uid not in chunk_ids_to_remove
        ]

        # Create new index and document map excluding the removed chunks
        new_index = faiss.IndexFlatL2(DIM)
        new_documents_map = {}
        new_faiss_id_map = {}
        vectors_to_add = []

        for uid, doc_info in kept:
            # IndexFlatL2 cannot remove or fetch vectors by uid; rebuild from content.
            vectors_to_add.append(_embed_documents([doc_info["content"]])[0])
            new_documents_map[uid] = {
                "file_path": doc_info["file_path"],
                "content": doc_info["content"],
                "faiss_id": len(vectors_to_add) - 1,
            }
            new_faiss_id_map[len(vectors_to_add) - 1] = uid

        if vectors_to_add:
            new_index.add(np.array(vectors_to_add, dtype="float32"))

        _index = new_index
        _documents_map = new_documents_map
        _faiss_id_to_uid = new_faiss_id_map
        _save_index_and_documents()  # Save the rebuilt index and map
        print(f"[Engine] Successfully removed chunks for {original_file_path}. New total vectors: {_index.ntotal}")


def search_index(query: str, k: int = 5) -> list[str]:
    """
    Performs a semantic search for the given query and returns the unique_chunk_ids of the top k results.
    """
    if not query.strip():
        return []

    with _index_lock:
        if _index.ntotal == 0:
            return ["⚠️ No files indexed yet. Please run /index first."]

    # Cache hit avoids model inference; embedding happens before taking the index lock.
    query_vec = np.array(_embed_query(query), dtype="float32").reshape(1, -1)

    with _index_lock:
        if _index.ntotal == 0:
            return ["⚠️ No files indexed yet. Please run /index first."]

        # Ensure the lookup table is in sync if the map was loaded from an older file.
        if len(_faiss_id_to_uid) != len(_documents_map):
            _rebuild_faiss_id_map()

        k_actual = min(k, _index.ntotal)
        if k_actual <= 0:
            return ["⚠️ No files indexed yet. Please run /index first."]

        _, indices = _index.search(query_vec, k_actual)

        results_unique_ids = []
        for faiss_id in indices[0]:
            uid = _faiss_id_to_uid.get(int(faiss_id))
            if uid is not None:
                results_unique_ids.append(uid)

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
