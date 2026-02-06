FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

# Evita prompts interactivos en apt
ENV DEBIAN_FRONTEND=noninteractive

# Proxy para el build (lo inyecta docker compose con build args)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY}

# System deps:
# - ffmpeg: descarga/extrae audio
# - ca-certificates: TLS correcto (muy común detrás de proxy)
# - tzdata: útil si guardas fechas y quieres zona horaria coherente (opcional pero recomendado)
# - libgomp1: a veces requerido por ctranslate2/whisper en CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    tzdata \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# (Opcional) fija timezone dentro del contenedor (si quieres)
# ENV TZ=Europe/Madrid

# Mejoras de pip detrás de proxy/certificados
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# IMPORTANTE:
# NO instales chromium aquí. Esta imagen ya trae los navegadores y dependencias.
# NO hagas: python -m playwright install chromium

COPY src ./src

# (Opcional) crea un directorio para outputs (videos, har, debug.png, etc.)
RUN mkdir -p /app/out

# Si tu main escribe ficheros, puedes forzar cwd o un path de salida en tu app.
# WORKDIR /app

CMD ["python", "-m", "src.main"]
