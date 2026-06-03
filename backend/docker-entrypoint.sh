#!/bin/sh
set -e

# Prima esecuzione: la directory migrations/ non esiste ancora
if [ ! -d "migrations" ]; then
    echo "[entrypoint] Prima esecuzione: inizializzazione migrazioni..."
    flask db init
    flask db migrate -m "init"
fi

echo "[entrypoint] Applicazione migrazioni..."
flask db upgrade

echo "[entrypoint] Creazione utenti iniziali (salta se esistono già)..."
flask seed-users

echo "[entrypoint] Avvio gunicorn..."
exec gunicorn --bind 0.0.0.0:9234 --workers 2 --timeout 60 main:app
