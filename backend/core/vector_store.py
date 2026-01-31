import faiss
import pickle
import numpy as np
import os
from backend.config import VECTOR_STORE_PATH

class VectorStore:
    def __init__(self, dimension=384): # MiniLM-L6-v2 is 384 dim
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = [] # List of dicts matching index
        self.load()

    def add(self, embeddings: list[list[float]], meta: list[dict]):
        if not embeddings:
            return
        
        vectors = np.array(embeddings).astype('float32')
        self.index.add(vectors)
        self.metadata.extend(meta)
        self.save()

    def search(self, query_vector: list[float], k=5):
        if self.index.ntotal == 0:
            return []
            
        params = np.array([query_vector]).astype('float32')
        distances, indices = self.index.search(params, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                results.append({
                    "score": float(distances[0][i]),
                    "metadata": self.metadata[idx]
                })
        return results

    def save(self):
        faiss.write_index(self.index, str(VECTOR_STORE_PATH))
        with open(str(VECTOR_STORE_PATH) + ".meta", "wb") as f:
            pickle.dump(self.metadata, f)

    def load(self):
        if os.path.exists(VECTOR_STORE_PATH):
            self.index = faiss.read_index(str(VECTOR_STORE_PATH))
            if os.path.exists(str(VECTOR_STORE_PATH) + ".meta"):
                with open(str(VECTOR_STORE_PATH) + ".meta", "rb") as f:
                    self.metadata = pickle.load(f)
