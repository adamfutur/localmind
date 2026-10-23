import os
import pickle
import threading

import faiss
import numpy as np

from backend.config import VECTOR_SAVE_INTERVAL, VECTOR_STORE_PATH

_instance = None
_instance_lock = threading.Lock()


class VectorStore:
    """In-process FAISS index with batched, atomic persistence.

    Previously every indexed file rewrote the whole index and pickle, which
    becomes O(n^2) and dominates indexing time. Saves are now batched and the
    instance is shared so search sees newly indexed vectors immediately.
    """

    def __init__(self, dimension=384):  # MiniLM-L6-v2 is 384 dim
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []  # List of dicts matching index
        self._lock = threading.RLock()
        self._pending_saves = 0
        self.load()

    def add(self, embeddings: list[list[float]], meta: list[dict]):
        if not embeddings:
            return

        with self._lock:
            vectors = np.array(embeddings).astype("float32")
            self.index.add(vectors)
            self.metadata.extend(meta)
            self._pending_saves += len(embeddings)

            if self._pending_saves >= VECTOR_SAVE_INTERVAL:
                self.save()

    def search(self, query_vector: list[float], k=5):
        with self._lock:
            if self.index.ntotal == 0:
                return []

            params = np.array([query_vector]).astype("float32")
            distances, indices = self.index.search(params, k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.metadata):
                    results.append({
                        "score": float(distances[0][i]),
                        "metadata": self.metadata[idx],
                    })
            return results

    def stats(self) -> dict:
        with self._lock:
            return {
                "vectors": int(self.index.ntotal),
                "vector_metadata": len(self.metadata),
            }

    def save(self):
        with self._lock:
            index_tmp = str(VECTOR_STORE_PATH) + ".tmp"
            meta_tmp = str(VECTOR_STORE_PATH) + ".meta.tmp"

            faiss.write_index(self.index, index_tmp)
            with open(meta_tmp, "wb") as f:
                pickle.dump(self.metadata, f, protocol=pickle.HIGHEST_PROTOCOL)

            os.replace(index_tmp, VECTOR_STORE_PATH)
            os.replace(meta_tmp, str(VECTOR_STORE_PATH) + ".meta")
            self._pending_saves = 0

    def load(self):
        with self._lock:
            if not os.path.exists(VECTOR_STORE_PATH):
                return

            self.index = faiss.read_index(str(VECTOR_STORE_PATH))
            meta_path = str(VECTOR_STORE_PATH) + ".meta"
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    self.metadata = pickle.load(f)


def get_vector_store() -> VectorStore:
    """Return the single shared index used by indexing and search."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = VectorStore()
    return _instance
