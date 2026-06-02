FROM python:3.12-slim

# Dipendenze di sistema: tesseract-ocr + client postgres
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ita \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Il codice viene montato via volume in compose.yaml,
# ma COPY serve per eventuali build standalone senza volume
COPY . .

RUN mkdir -p uploads

EXPOSE 8129

ENTRYPOINT ["/bin/sh", "-c"]
# flask db upgrade applica le migrazioni pendenti (idempotente)
CMD ["flask db upgrade && gunicorn --bind 0.0.0.0:8129 --workers 2 --timeout 60 main:app"]
