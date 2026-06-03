FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ita \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Il codice viene montato via volume in compose.yaml;
# COPY serve per build standalone senza volume
COPY . .

RUN mkdir -p uploads && chmod +x docker-entrypoint.sh

EXPOSE 9234

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
