import os

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")

# Modelo Embeddings
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

# Configuración de chunks
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# Directorio FAISS
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "/app/shared/faiss_index")
FAISS_INDEX_FILE = os.getenv("FAISS_INDEX_FILE", "index.faiss")
FAISS_METADATA_FILE = os.getenv("FAISS_METADATA_FILE", "metadata.pkl")

# Intervalo procesamiento
PROCESSING_INTERVAL = int(os.getenv("PROCESSING_INTERVAL", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

# Groq configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "3000"))