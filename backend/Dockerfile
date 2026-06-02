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

COPY . .

RUN mkdir -p uploads

EXPOSE 8129

# Gunicorn in produzione; 2 worker sincroni sono sufficienti per questa app
CMD ["gunicorn", "--bind", "0.0.0.0:8129", "--workers", "2", "--timeout", "60", "main:app"]
