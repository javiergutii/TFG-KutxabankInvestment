FROM python:3.11-slim

# Argumentos para proxy (opcional)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Configurar proxy si se proporciona
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ /app/src/

# Crear directorio para índice FAISS
RUN mkdir -p /app/shared/faiss_index

# Comando por defecto
CMD ["python", "-m", "src.main"]