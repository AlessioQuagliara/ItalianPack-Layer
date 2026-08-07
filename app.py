import os
from pathlib import Path

from flask import Flask, jsonify
from flask_admin import Admin

from bancale_api import bancale_bp
from bancale_views import CaricaCommessaView, CommesseListView
from db_migration import migrate_schema, migrate_rotazione
from models import db
from views import (
    CartelloView,
    DashboardIndexView,
    EtichetteBarcodeView,
    EtichetteNoBarcodeView,
    EtichetteVitiView,
)

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-etichette-dashboard")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(BASE_DIR / "gestionale.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(bancale_bp)

with app.app_context():
    db.create_all()
    migrate_schema(db)
    migrate_rotazione(db)


@app.errorhandler(413)
def too_large(_exc):
    return jsonify(error="File troppo grande (limite 25 MB)."), 413


admin = Admin(
    app,
    name="Dashboard Automazioni",
    url="/",
    index_view=DashboardIndexView(name="Home", url="/"),
)

admin.add_view(EtichetteBarcodeView(
    name="Con Barcode",
    endpoint="etichette_barcode",
    url="/etichette/barcode",
    category="Stampa Etichette",
))
admin.add_view(EtichetteNoBarcodeView(
    name="Senza Barcode",
    endpoint="etichette_no_barcode",
    url="/etichette/no-barcode",
    category="Stampa Etichette",
))
admin.add_view(EtichetteVitiView(
    name="Viti (Speciali)",
    endpoint="etichette_viti",
    url="/etichette/viti",
    category="Stampa Etichette",
))

admin.add_view(CartelloView(
    name="Genera Cartello",
    endpoint="cartelli",
    url="/cartelli",
    category="Cartelli",
))

admin.add_view(CaricaCommessaView(
    name="Carica Distinta",
    endpoint="carica_commessa",
    url="/commesse/carica",
    category="Mappatura Bancale",
))
admin.add_view(CommesseListView(
    name="Commesse",
    endpoint="commesse",
    url="/commesse",
    category="Mappatura Bancale",
))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
