from pathlib import Path


# Project Paths

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
PROMPTS_DIR = BASE_DIR / "app" / "prompts"


# Models
LLM_MODEL = "deepseek-r1:7b"
EMBEDDING_MODEL = "nomic-embed-text"


# Chunk Settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


# Retrieval
TOP_K_RESULTS = 3


# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"