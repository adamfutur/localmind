from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL_NAME

class EmbeddingModel:
    def __init__(self):
        # This will download the model on first run
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.model.encode(texts).tolist()
    
    def embed_query(self, query: str) -> list[float]:
        return self.model.encode([query])[0].tolist()
