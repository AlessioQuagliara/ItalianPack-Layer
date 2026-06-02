#!/bin/bash
# setup.sh – eseguire UNA SOLA VOLTA per inizializzare PartFlow
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Setup PartFlow ===${NC}"

# 1. Crea .env se non esiste
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env creato da .env.example${NC}"
    echo "  → Modifica SECRET_KEY e POSTGRES_PASSWORD prima di continuare (opzionale per dev)"
fi

# 2. Build immagine
echo -e "\n${YELLOW}Build immagine Docker...${NC}"
docker compose build

# 3. Avvia solo il DB e aspetta che sia pronto
echo -e "\n${YELLOW}Avvio PostgreSQL...${NC}"
docker compose up -d db
echo "  Attendo che il DB sia pronto..."
sleep 5

# 4. Inizializza Flask-Migrate (crea backend/migrations/)
echo -e "\n${YELLOW}Inizializzazione migrazioni...${NC}"
docker compose run --rm app sh -c "flask db init"

# 5. Crea la prima migrazione
echo -e "\n${YELLOW}Creazione migrazione iniziale...${NC}"
docker compose run --rm app sh -c "flask db migrate -m 'init'"

# 6. Applica le migrazioni al DB
echo -e "\n${YELLOW}Applicazione migrazioni al DB...${NC}"
docker compose run --rm app sh -c "flask db upgrade"

# 7. Crea l'utente admin iniziale
echo -e "\n${YELLOW}Creazione utente admin...${NC}"
docker compose run --rm app sh -c "flask seed-users"

# 8. Avvia tutto
echo -e "\n${YELLOW}Avvio completo...${NC}"
docker compose up -d

echo -e "\n${GREEN}=== PartFlow è pronto! ===${NC}"
echo -e "  URL locale:  http://localhost:8129/auth/login"
echo -e "  URL LAN:     http://$(hostname -I | awk '{print $1}'):8129/auth/login"
echo -e ""
echo -e "  admin     / admin123      (ruolo: admin)"
echo -e "  marco     / tecnico123    (ruolo: tecnico)"
echo -e "  sara      / magazzino123  (ruolo: magazzino)"
