import os

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")

# Modelo Embeddings
# CAMBIO: paraphrase-multilingual-mpnet-base-v2 es más potente para búsqueda cross-language
# (español → inglés) que el MiniLM anterior
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

# Configuración de chunks
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))  # subido de 30 a 50

# Directorio FAISS
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "/app/shared/faiss_index")
FAISS_INDEX_FILE = os.getenv("FAISS_INDEX_FILE", "index.faiss")
FAISS_METADATA_FILE = os.getenv("FAISS_METADATA_FILE", "metadata.pkl")

# Intervalo procesamiento
PROCESSING_INTERVAL = int(os.getenv("PROCESSING_INTERVAL", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

# Ollama configuración
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "800"))