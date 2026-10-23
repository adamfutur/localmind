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

# Performance tuning (all overridable through environment variables)
# FastEmbed/ONNX is much lighter and faster on CPU than PyTorch. "auto" uses it
# when installed and falls back to sentence-transformers.
EMBED_BACKEND = os.getenv("LOCALMIND_EMBED_BACKEND", "auto").lower()
FASTEMBED_MODEL_NAME = os.getenv(
    "LOCALMIND_FASTEMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBED_BATCH_SIZE = int(os.getenv("LOCALMIND_EMBED_BATCH", "32"))
# Saving the full FAISS index after every file is O(n^2); batch it instead.
VECTOR_SAVE_INTERVAL = int(os.getenv("LOCALMIND_VECTOR_SAVE_INTERVAL", "2000"))
# Bounded cache for repeated query embeddings (cold queries still hit the model).
QUERY_CACHE_SIZE = int(os.getenv("LOCALMIND_QUERY_CACHE_SIZE", "256"))

# Only scan/parse files we can actually embed, and skip huge files.
SUPPORTED_EXTENSIONS = frozenset({
    ".txt", ".md", ".markdown", ".rst",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".html", ".htm", ".css", ".scss", ".less",
    ".json", ".jsonl", ".csv", ".xml", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".sql", ".sh", ".ps1", ".bat", ".log",
})
MAX_FILE_SIZE_MB = int(os.getenv("LOCALMIND_MAX_FILE_MB", "2"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# LLM Settings (can be configured via ENV)
# For local-first, we might default to a local LLM or OpenAI compatible endpoint
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1") # Default to Ollama
