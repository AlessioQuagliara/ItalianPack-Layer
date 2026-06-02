# models/panthera_sync_log.py
from core.db import db


class PantheraSyncLog(db.Model):
    __tablename__ = 'panthera_sync_logs'

    id         = db.Column(db.Integer, primary_key=True)
    status     = db.Column(
        db.Enum('success', 'partial', 'failed', name='sync_status'),
        nullable=False
    )
    ordini_importati   = db.Column(db.Integer, default=0)
    ordini_aggiornati  = db.Column(db.Integer, default=0)
    errori             = db.Column(db.Integer, default=0)
    messaggio          = db.Column(db.Text, nullable=True)          # dettaglio errore se fallisce
    payload_raw        = db.Column(db.JSON, nullable=True)          # risposta grezza Panthera
    created_at         = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<SyncLog {self.id} [{self.status}] {self.created_at}>'
