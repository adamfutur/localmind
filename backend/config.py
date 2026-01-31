import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "metadata_v2.db"
VECTOR_STORE_PATH = DATA_DIR / "vectors.faiss"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Settings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# LLM Settings (can be configured via ENV)
# For local-first, we might default to a local LLM or OpenAI compatible endpoint
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1") # Default to Ollama
