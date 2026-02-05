FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para Playwright/Chromium + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    wget \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Asegura Playwright (por si no está en requirements) e instala Chromium
RUN pip install --no-cache-dir playwright \
    && python -m playwright install chromium

COPY src ./src

CMD ["python", "-m", "src.main"]
