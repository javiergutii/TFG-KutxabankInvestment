# Usamos la imagen del extractor ya construida localmente
# (evita descargar de Docker Hub, que está bloqueado por el proxy)
FROM tfg-extractor:latest

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app

# Instalar dependencias adicionales del processor
# (el extractor ya tiene: playwright, faster-whisper, mysql-connector, requests, python-dotenv)
COPY requirements.txt /tmp/processor_requirements.txt
RUN pip install --no-cache-dir \
    --proxy=${HTTP_PROXY} \
    -r /tmp/processor_requirements.txt

RUN mkdir -p /app/shared/faiss_index

CMD ["python", "main.py"]