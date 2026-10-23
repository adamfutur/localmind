import threading
from collections import OrderedDict

from backend.config import (
    EMBED_BACKEND,
    EMBED_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    FASTEMBED_MODEL_NAME,
    QUERY_CACHE_SIZE,
)

_model_lock = threading.Lock()
_model_instance = None


class EmbeddingModel:
    """Embedding model that prefers FastEmbed/ONNX and falls back to PyTorch.

    FastEmbed uses roughly 5-10x less RAM and is noticeably faster on CPU,
    which matters on 8 GB laptops. Both backends use an all-MiniLM-L6-v2
    model (384 dimensions) so the FAISS index layout stays the same.
    """

    def __init__(self):
        self.backend = None
        self.model = None
        self._encode_lock = threading.Lock()
        self._query_cache = OrderedDict()  # bounded LRU: query -> tuple[float, ...]
        self._query_cache_lock = threading.Lock()
        self._load()

    def _load(self):
        errors = []

        if EMBED_BACKEND in ("auto", "fastembed"):
            try:
                from fastembed import TextEmbedding

                self.model = TextEmbedding(model_name=FASTEMBED_MODEL_NAME)
                self.backend = "fastembed"
                print(f"[Embeddings] Using FastEmbed ({FASTEMBED_MODEL_NAME})")
                return
            except Exception as exc:  # pragma: no cover - depends on install
                errors.append(f"fastembed: {exc}")
                if EMBED_BACKEND == "fastembed":
                    raise

        if EMBED_BACKEND in ("auto", "sentence-transformers", "torch"):
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                self.backend = "sentence-transformers"
                print(f"[Embeddings] Using sentence-transformers ({EMBEDDING_MODEL_NAME})")
                return
            except Exception as exc:  # pragma: no cover - depends on install
                errors.append(f"sentence-transformers: {exc}")

        raise RuntimeError(
            "No embedding backend available. Install fastembed "
            "(`pip install -r backend/requirements.txt`) or sentence-transformers. "
            + " | ".join(errors)
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        with self._encode_lock:
            if self.backend == "fastembed":
                vectors = self.model.embed(texts, batch_size=EMBED_BATCH_SIZE)
                return [vector.tolist() for vector in vectors]

            vectors = self.model.encode(
                texts,
                batch_size=EMBED_BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        key = query.strip()

        with self._query_cache_lock:
            cached = self._query_cache.get(key)
            if cached is not None:
                self._query_cache.move_to_end(key)
                return list(cached)

        vector = self.embed([key])[0]

        with self._query_cache_lock:
            self._query_cache[key] = tuple(vector)
            self._query_cache.move_to_end(key)
            while len(self._query_cache) > QUERY_CACHE_SIZE:
                self._query_cache.popitem(last=False)

        return vector


def get_embedding_model() -> EmbeddingModel:
    """Return one process-wide model to avoid loading it several times."""
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                _model_instance = EmbeddingModel()
    return _model_instance
