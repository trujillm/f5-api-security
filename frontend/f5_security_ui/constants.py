"""
Shared constants for the streamlit UI application.
"""

# Vector Database Configuration
DEFAULT_VECTOR_DB_NAME = "demo-vector-db"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_CHUNK_SIZE_TOKENS = 512

# LLM Configuration
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 1000
DEFAULT_REPETITION_PENALTY = 1.1

# Default Endpoint Configuration
DEFAULT_XC_URL = "http://llamastack:8321"  # Default to local LlamaStack
