import uuid
from pathlib import Path

from flask import request, flash, redirect, url_for, jsonify
from flask_admin import BaseView, expose
from werkzeug.utils import secure_filename

from bancale_excel import read_distinta
from models import db, Commessa, RigaCommessa, STATI_COMMESSA, STATI_LABEL

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}


class CommesseListView(BaseView):
    @expose("/", methods=["GET"])
    def index(self):
        commesse = Commessa.query.order_by(Commessa.creato_il.desc()).all()
        azioni_base = url_for(".index").rstrip("/")
        return self.render(
            "bancale/commesse.html",
            commesse=commesse,
            stati=STATI_COMMESSA,
            stati_label=STATI_LABEL,
            azioni_base=azioni_base,
        )

    @expose("/stato-multiplo", methods=["POST"])
    def aggiorna_stato_multiplo(self):
        data = request.get_json(silent=True) or {}
        ids = data.get("ids") or []
        stato = data.get("stato")

        if stato not in STATI_COMMESSA:
            return jsonify(error="Stato non valido."), 400
        if not isinstance(ids, list) or not ids:
            return jsonify(error="Nessuna commessa selezionata."), 400

        commesse = Commessa.query.filter(Commessa.id.in_(ids)).all()
        for c in commesse:
            c.stato = stato
        db.session.commit()

        return jsonify(aggiornate=[
            {"id": c.id, "stato": c.stato, "stato_label": c.stato_label} for c in commesse
        ])

    @expose("/<int:commessa_id>/elimina", methods=["POST"])
    def elimina(self, commessa_id):
        commessa = Commessa.query.get_or_404(commessa_id)
        db.session.delete(commessa)
        db.session.commit()
        return jsonify(ok=True)


class CaricaCommessaView(BaseView):
    @expose("/", methods=["GET"])
    def index(self):
        return self.render("bancale/carica.html")

    @expose("/carica", methods=["POST"])
    def carica(self):
        nome = (request.form.get("nome") or "").strip()
        file = request.files.get("excel_file")

        if not nome:
            flash("Il nome della commessa è obbligatorio.", "error")
            return redirect(url_for(".index"))
        if not file or file.filename == "":
            flash("Nessun file selezionato.", "error")
            return redirect(url_for(".index"))

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            flash("Formato non valido. Carica un file .xlsx", "error")
            return redirect(url_for(".index"))

        safe_name = secure_filename(file.filename) or "distinta.xlsx"
        saved_path = UPLOAD_DIR / f"bancale_{uuid.uuid4().hex}_{safe_name}"
        file.save(saved_path)

        try:
            righe = read_distinta(saved_path)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for(".index"))

        commessa = Commessa(nome=nome)
        db.session.add(commessa)
        db.session.flush()

        for record in righe:
            db.session.add(RigaCommessa(commessa_id=commessa.id, **record))

        db.session.commit()
        flash(f"Commessa '{nome}' creata con {len(righe)} righe.", "success")
        return redirect(url_for("bancale.mappa", commessa_id=commessa.id))
