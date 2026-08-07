from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

STATI_COMMESSA = ["da_fare", "in_corso", "fatto"]
STATI_LABEL = {"da_fare": "Da fare", "in_corso": "In corso", "fatto": "Già fatto"}

# Scala 1:10 (1 cm = 10 px) per tutti i contenitori e le vaschette.
VASCHETTA_DIMENSIONI = {
    "slim": {"w": 600, "h": 130},
    "medium": {"w": 600, "h": 270},
    "big": {"w": 600, "h": 400},
}

TIPI_CONTENITORE = ["bancale", "scaffale", "carrello"]
TIPI_CONTENITORE_LABEL = {
    "bancale": "Bancale (EPAL)",
    "scaffale": "Scaffale (ripiano)",
    "carrello": "Carrello",
}

# Dimensioni reali in cm -> px (scala 1:10):
# - Bancale EPAL: 120x80 cm orizzontale
# - Scaffale: ogni ripiano è un'area indipendente 60x120 cm
# - Carrello: misura standard proposta 100x60 cm
CONTENITORE_DIMENSIONI = {
    "bancale": {"w": 1200, "h": 800},
    "scaffale": {"w": 600, "h": 1200},
    "carrello": {"w": 1000, "h": 600},
}


def _now():
    return datetime.now(timezone.utc)


class Commessa(db.Model):
    __tablename__ = "commessa"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    stato = db.Column(db.String(20), nullable=False, default="da_fare")
    creato_il = db.Column(db.DateTime, default=_now)

    righe = db.relationship(
        "RigaCommessa", backref="commessa", cascade="all, delete-orphan", lazy="selectin"
    )
    contenitori = db.relationship(
        "Contenitore",
        backref="commessa",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Contenitore.numero",
    )

    @property
    def stato_label(self):
        return STATI_LABEL.get(self.stato, self.stato)

    @property
    def numero_righe(self):
        return len(self.righe)

    def __str__(self):
        return self.nome


class RigaCommessa(db.Model):
    __tablename__ = "riga_commessa"

    id = db.Column(db.Integer, primary_key=True)
    commessa_id = db.Column(db.Integer, db.ForeignKey("commessa.id"), nullable=False, index=True)

    codice = db.Column(db.String(100))
    descrizione = db.Column(db.String(500))
    cassetto = db.Column(db.String(50))
    ubicazione = db.Column(db.String(50))
    quantita = db.Column(db.Float)
    mancanti = db.Column(db.Float)
    rda = db.Column(db.String(100))
    avanzi = db.Column(db.Float)
    gruppo = db.Column(db.String(100), index=True)
    descrizione_gruppo = db.Column(db.String(500))

    def __str__(self):
        return self.codice or ""


class Contenitore(db.Model):
    """Un supporto fisico indipendente (bancale, ripiano di scaffale, carrello)
    su cui vengono piazzate le vaschette. Una Commessa può avere N contenitori."""

    __tablename__ = "contenitore"

    id = db.Column(db.Integer, primary_key=True)
    commessa_id = db.Column(db.Integer, db.ForeignKey("commessa.id"), nullable=False, index=True)

    tipo = db.Column(db.String(30), nullable=False, default="bancale")
    numero = db.Column(db.Integer, nullable=False, default=1)
    etichetta = db.Column(db.String(100), nullable=True)

    vaschette = db.relationship(
        "MappaturaBancale", backref="contenitore", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def nome_visualizzato(self):
        if self.etichetta:
            return self.etichetta
        return f"{TIPI_CONTENITORE_LABEL.get(self.tipo, self.tipo.title())} {self.numero}"

    @property
    def dimensioni(self):
        return CONTENITORE_DIMENSIONI.get(self.tipo, CONTENITORE_DIMENSIONI["bancale"])

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "numero": self.numero,
            "nome": self.nome_visualizzato,
            "w": self.dimensioni["w"],
            "h": self.dimensioni["h"],
        }


class MappaturaBancale(db.Model):
    __tablename__ = "mappatura_bancale"

    id = db.Column(db.Integer, primary_key=True)
    contenitore_id = db.Column(db.Integer, db.ForeignKey("contenitore.id"), nullable=False, index=True)

    tipo = db.Column(db.String(20), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    gruppo = db.Column(db.String(100), nullable=True)
    ruotata = db.Column(db.Boolean, nullable=False, default=False)

    aggiornato_il = db.Column(db.DateTime, default=_now, onupdate=_now)

    def to_dict(self):
        dims = VASCHETTA_DIMENSIONI.get(self.tipo, {"w": 0, "h": 0})
        w, h = dims["w"], dims["h"]
        if self.ruotata:
            w, h = h, w
        return {
            "id": self.id,
            "tipo": self.tipo,
            "x": self.x,
            "y": self.y,
            "w": w,
            "h": h,
            "ruotata": bool(self.ruotata),
            "gruppo": self.gruppo,
        }
