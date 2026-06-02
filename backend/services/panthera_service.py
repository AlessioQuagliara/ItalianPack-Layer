# services/panthera_service.py
# Servizio per l'integrazione con Panthera ERP
import requests
from datetime import datetime
from flask import current_app

from core.db import db
from models.panthera_order import PantheraOrder
from models.panthera_sync_log import PantheraSyncLog


class PantheraService:

    def __init__(self):
        self.base_url = current_app.config.get('PANTHERA_BASE_URL', '')
        self.api_key  = current_app.config.get('PANTHERA_API_KEY', '')
        self.headers  = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    # ------------------------------------------------------------------
    # Metodi HTTP interni
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Esegue una GET su Panthera e restituisce il JSON."""
        url = f'{self.base_url}{endpoint}'
        risposta = requests.get(url, headers=self.headers, params=params, timeout=15)
        risposta.raise_for_status()
        return risposta.json()

    # ------------------------------------------------------------------
    # Sincronizzazione ordini
    # ------------------------------------------------------------------

    def fetch_ordini(self) -> list[dict]:
        """Recupera la lista ordini da Panthera."""
        dati = self._get('/api/ordini')
        return dati.get('data', dati) if isinstance(dati, dict) else dati

    def sync_ordini(self) -> PantheraSyncLog:
        """
        Importa gli ordini da Panthera e li salva su PostgreSQL.
        Crea un PantheraSyncLog con il risultato dell'operazione.
        """
        importati  = 0
        aggiornati = 0
        errori     = 0
        payload    = None

        try:
            ordini_raw = self.fetch_ordini()
            payload    = ordini_raw

            for raw in ordini_raw:
                try:
                    panthera_id = str(raw.get('id') or raw.get('panthera_id'))
                    ordine_esistente = PantheraOrder.query.filter_by(panthera_id=panthera_id).first()

                    if ordine_esistente:
                        # Aggiorna il record esistente
                        ordine_esistente.panthera_code  = raw.get('code')
                        ordine_esistente.customer_name  = raw.get('customer_name')
                        ordine_esistente.customer_code  = raw.get('customer_code')
                        ordine_esistente.order_type     = raw.get('order_type')
                        ordine_esistente.status         = raw.get('status', 'pending')
                        ordine_esistente.raw_json       = raw
                        ordine_esistente.synced_at      = datetime.utcnow()
                        aggiornati += 1
                    else:
                        # Inserisce nuovo record
                        nuovo = PantheraOrder(
                            panthera_id    = panthera_id,
                            panthera_code  = raw.get('code'),
                            customer_name  = raw.get('customer_name'),
                            customer_code  = raw.get('customer_code'),
                            order_type     = raw.get('order_type'),
                            status         = raw.get('status', 'pending'),
                            raw_json       = raw,
                            synced_at      = datetime.utcnow(),
                        )
                        db.session.add(nuovo)
                        importati += 1

                except Exception:
                    errori += 1

            db.session.commit()
            stato = 'success' if errori == 0 else 'partial'

        except Exception as e:
            db.session.rollback()
            stato  = 'failed'
            errori += 1
            log = PantheraSyncLog(
                status            = 'failed',
                ordini_importati  = 0,
                ordini_aggiornati = 0,
                errori            = 1,
                messaggio         = str(e),
                payload_raw       = payload,
            )
            db.session.add(log)
            db.session.commit()
            return log

        log = PantheraSyncLog(
            status            = stato,
            ordini_importati  = importati,
            ordini_aggiornati = aggiornati,
            errori            = errori,
            payload_raw       = payload,
        )
        db.session.add(log)
        db.session.commit()
        return log
