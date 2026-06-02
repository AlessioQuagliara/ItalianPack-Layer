# services/ocr_service.py
# Servizio OCR per l'elaborazione degli scontrini
import re
import threading
from datetime import datetime, date
from pathlib import Path

from flask import current_app

from core.db import db
from models.receipt import Receipt


class OcrService:
    """
    Esegue il riconoscimento testo su immagini scontrino.
    Motore configurabile via OCR_ENGINE: 'tesseract' (default) o 'google_vision'.
    """

    def __init__(self, app=None):
        self.app = app

    # ------------------------------------------------------------------
    # Estrazione testo
    # ------------------------------------------------------------------

    def _ocr_tesseract(self, filepath: str) -> str:
        """Usa pytesseract per estrarre testo dall'immagine."""
        import pytesseract
        from PIL import Image
        from flask import current_app

        pytesseract.pytesseract.tesseract_cmd = current_app.config.get(
            'TESSERACT_CMD', 'tesseract'
        )
        img = Image.open(filepath)
        return pytesseract.image_to_string(img, lang='ita')

    def _ocr_google_vision(self, filepath: str) -> str:
        """Usa Google Vision API per estrarre testo dall'immagine."""
        import base64
        import requests
        from flask import current_app

        api_key = current_app.config.get('GOOGLE_VISION_API_KEY', '')
        with open(filepath, 'rb') as f:
            contenuto = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            'requests': [{
                'image': {'content': contenuto},
                'features': [{'type': 'TEXT_DETECTION'}],
            }]
        }
        url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
        risposta = requests.post(url, json=payload, timeout=15)
        risposta.raise_for_status()
        dati = risposta.json()
        try:
            return dati['responses'][0]['fullTextAnnotation']['text']
        except (KeyError, IndexError):
            return ''

    def estrai_testo(self, filepath: str) -> str:
        """Sceglie il motore OCR in base alla configurazione."""
        from flask import current_app
        motore = current_app.config.get('OCR_ENGINE', 'tesseract')
        if motore == 'google_vision':
            return self._ocr_google_vision(filepath)
        return self._ocr_tesseract(filepath)

    # ------------------------------------------------------------------
    # Parsing dati dal testo grezzo
    # ------------------------------------------------------------------

    def _parse_data(self, testo: str):
        """Cerca una data nel testo (formati: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)."""
        pattern = r'(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})'
        match = re.search(pattern, testo)
        if not match:
            return None
        stringa = match.group(1).replace('-', '/')
        try:
            parti = stringa.split('/')
            if len(parti[0]) == 4:
                return date(int(parti[0]), int(parti[1]), int(parti[2]))
            return date(int(parti[2]), int(parti[1]), int(parti[0]))
        except ValueError:
            return None

    def _parse_totale(self, testo: str):
        """Cerca un importo totale nel testo (es: TOTALE 12,50 o € 12.50)."""
        pattern = r'(?:totale|total|importo)\D{0,10}(\d+[.,]\d{2})'
        match = re.search(pattern, testo, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', '.'))
            except ValueError:
                return None
        return None

    def _parse_fornitore(self, testo: str) -> str | None:
        """Prende la prima riga non vuota come nome fornitore (euristica)."""
        for riga in testo.splitlines():
            riga = riga.strip()
            if riga and len(riga) > 3:
                return riga[:128]
        return None

    # ------------------------------------------------------------------
    # Elaborazione asincrona
    # ------------------------------------------------------------------

    def _elabora_receipt(self, receipt_id: int, filepath: str, app):
        """Eseguito in un thread separato per non bloccare la request."""
        with app.app_context():
            receipt = Receipt.query.get(receipt_id)
            if not receipt:
                return
            try:
                testo_grezzo          = self.estrai_testo(filepath)
                receipt.ocr_raw_text  = testo_grezzo
                receipt.ocr_date      = self._parse_data(testo_grezzo)
                receipt.ocr_total     = self._parse_totale(testo_grezzo)
                receipt.ocr_supplier  = self._parse_fornitore(testo_grezzo)
                receipt.status        = 'ocr_done'
            except Exception as e:
                receipt.status = 'rejected'
                receipt.notes  = f'Errore OCR: {e}'
            finally:
                db.session.commit()

    def avvia_ocr_asincrono(self, receipt_id: int, filepath: str, app):
        """Lancia l'elaborazione OCR in background."""
        thread = threading.Thread(
            target=self._elabora_receipt,
            args=(receipt_id, filepath, app),
            daemon=True,
        )
        thread.start()
