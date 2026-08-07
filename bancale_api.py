from flask import Blueprint, render_template, request, jsonify, url_for, send_file, abort

import cartello_job
import label_jobs
from jobs import create_job, get_job, run_in_background
from models import (
    db,
    Commessa,
    RigaCommessa,
    Contenitore,
    MappaturaBancale,
    VASCHETTA_DIMENSIONI,
    TIPI_CONTENITORE,
)

bancale_bp = Blueprint("bancale", __name__, url_prefix="/bancale")

# Tolleranza contro rumore in virgola mobile nelle coordinate calcolate lato
# client (drag diviso per lo scale factor, ecc.): evita falsi rifiuti quando
# una posizione è concettualmente esatta (es. esattamente a contatto con un
# bordo) ma arriva come 599.9999999999999 invece di 600.
_EPS = 0.5


def _dimensioni_effettive(tipo, ruotata):
    dims = VASCHETTA_DIMENSIONI.get(tipo, {"w": 0, "h": 0})
    if ruotata:
        return dims["h"], dims["w"]
    return dims["w"], dims["h"]


def _posizione_valida(contenitore, x, y, w, h, escludi_id=None):
    dims = contenitore.dimensioni
    if x < -_EPS or y < -_EPS or x + w > dims["w"] + _EPS or y + h > dims["h"] + _EPS:
        return False

    query = MappaturaBancale.query.filter_by(contenitore_id=contenitore.id)
    if escludi_id is not None:
        query = query.filter(MappaturaBancale.id != escludi_id)

    for altra in query.all():
        # BUG storico: qui si usavano le dimensioni "di base" del tipo, senza
        # considerare se la vaschetta vicina fosse ruotata. Una vaschetta
        # ruotata ha un ingombro reale diverso (w/h invertiti): non tenerne
        # conto creava una "zona di collisione fantasma" scorretta, che
        # bloccava posizionamenti in aree in realtà libere.
        aw, ah = _dimensioni_effettive(altra.tipo, altra.ruotata)
        if (
            x < altra.x + aw - _EPS
            and x + w > altra.x + _EPS
            and y < altra.y + ah - _EPS
            and y + h > altra.y + _EPS
        ):
            return False

    return True


def _crea_contenitore_default(commessa_id):
    contenitore = Contenitore(commessa_id=commessa_id, tipo="bancale", numero=1)
    db.session.add(contenitore)
    db.session.commit()
    return contenitore


@bancale_bp.route("/<int:commessa_id>/mappa")
@bancale_bp.route("/<int:commessa_id>/mappa/<int:contenitore_id>")
def mappa(commessa_id, contenitore_id=None):
    commessa = Commessa.query.get_or_404(commessa_id)

    if not commessa.contenitori:
        _crea_contenitore_default(commessa_id)
        db.session.refresh(commessa)

    if contenitore_id is None:
        contenitore = commessa.contenitori[0]
    else:
        contenitore = next((c for c in commessa.contenitori if c.id == contenitore_id), None)
        if contenitore is None:
            abort(404)

    righe_json = [
        {
            "codice": r.codice,
            "descrizione": r.descrizione,
            "gruppo": r.gruppo,
            "descrizione_gruppo": r.descrizione_gruppo,
        }
        for r in commessa.righe
    ]
    vaschette_json = [v.to_dict() for v in contenitore.vaschette]
    contenitori_json = [c.to_dict() for c in commessa.contenitori]

    # Indice leggero (gruppo -> dove si trova) per la ricerca articoli tra TUTTI
    # i supporti della commessa, non solo quello attivo.
    ricerca_globale_json = [
        {"contenitore_id": c.id, "vaschetta_id": v.id, "gruppo": v.gruppo}
        for c in commessa.contenitori
        for v in c.vaschette
        if v.gruppo
    ]

    vaschetta_item_base = url_for("bancale.vaschetta_item", vaschetta_id=1).rsplit("/", 1)[0]
    vista_lettura = request.args.get("vista") == "1"

    return render_template(
        "bancale/mappa.html",
        commessa=commessa,
        contenitore=contenitore,
        contenitori=commessa.contenitori,
        contenitori_json=contenitori_json,
        righe_json=righe_json,
        vaschette_json=vaschette_json,
        ricerca_globale_json=ricerca_globale_json,
        vaschetta_item_base=vaschetta_item_base,
        vaschette_url=url_for("bancale.vaschette_collection", contenitore_id=contenitore.id),
        nomi_cartelli=cartello_job.NOMI_CARTELLI,
        vista_lettura=vista_lettura,
    )


@bancale_bp.route("/<int:commessa_id>/contenitori", methods=["GET", "POST"])
def contenitori_collection(commessa_id):
    commessa = Commessa.query.get_or_404(commessa_id)

    if request.method == "GET":
        return jsonify([c.to_dict() for c in commessa.contenitori])

    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")
    etichetta_custom = (data.get("etichetta") or "").strip() or None

    if tipo not in TIPI_CONTENITORE:
        return jsonify(error="Tipo di supporto non valido."), 400

    esistenti_stesso_tipo = Contenitore.query.filter_by(commessa_id=commessa_id, tipo=tipo).count()
    nuovi = []

    if tipo == "scaffale":
        numero = (esistenti_stesso_tipo // 5) + 1
        base_nome = etichetta_custom or "Scaffale"
        for ripiano in range(1, 6):
            c = Contenitore(
                commessa_id=commessa_id,
                tipo=tipo,
                numero=numero,
                etichetta=f"{base_nome} {numero} · Ripiano {ripiano}",
            )
            db.session.add(c)
            nuovi.append(c)
    else:
        numero = esistenti_stesso_tipo + 1
        c = Contenitore(commessa_id=commessa_id, tipo=tipo, numero=numero, etichetta=etichetta_custom)
        db.session.add(c)
        nuovi.append(c)

    db.session.commit()
    return jsonify([c.to_dict() for c in nuovi]), 201


@bancale_bp.route("/contenitori/<int:contenitore_id>/elimina", methods=["POST"])
def elimina_contenitore(contenitore_id):
    contenitore = Contenitore.query.get_or_404(contenitore_id)
    commessa_id = contenitore.commessa_id

    rimanenti = Contenitore.query.filter_by(commessa_id=commessa_id).count()
    if rimanenti <= 1:
        return jsonify(error="Non puoi eliminare l'ultimo supporto della commessa."), 400

    db.session.delete(contenitore)
    db.session.commit()
    return jsonify(ok=True)


@bancale_bp.route("/contenitore/<int:contenitore_id>/vaschette", methods=["GET", "POST"])
def vaschette_collection(contenitore_id):
    contenitore = Contenitore.query.get_or_404(contenitore_id)

    if request.method == "GET":
        return jsonify([v.to_dict() for v in contenitore.vaschette])

    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")
    x = data.get("x")
    y = data.get("y")
    ruotata = bool(data.get("ruotata", False))

    if tipo not in VASCHETTA_DIMENSIONI:
        return jsonify(error="Tipo vaschetta non valido."), 400
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return jsonify(error="Coordinate non valide."), 400

    w, h = _dimensioni_effettive(tipo, ruotata)
    if not _posizione_valida(contenitore, x, y, w, h):
        return jsonify(error="Posizione non valida: fuori dal supporto o in collisione con un'altra vaschetta."), 400

    vaschetta = MappaturaBancale(contenitore_id=contenitore_id, tipo=tipo, x=x, y=y, ruotata=ruotata)
    db.session.add(vaschetta)
    db.session.commit()
    return jsonify(vaschetta.to_dict()), 201


@bancale_bp.route("/vaschette/<int:vaschetta_id>", methods=["PATCH", "DELETE"])
def vaschetta_item(vaschetta_id):
    vaschetta = MappaturaBancale.query.get_or_404(vaschetta_id)

    if request.method == "DELETE":
        db.session.delete(vaschetta)
        db.session.commit()
        return jsonify(ok=True)

    data = request.get_json(silent=True) or {}

    if "x" in data or "y" in data or "ruotata" in data:
        x = data.get("x", vaschetta.x)
        y = data.get("y", vaschetta.y)
        ruotata = bool(data.get("ruotata", vaschetta.ruotata))

        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return jsonify(error="Coordinate non valide."), 400

        w, h = _dimensioni_effettive(vaschetta.tipo, ruotata)
        if not _posizione_valida(vaschetta.contenitore, x, y, w, h, escludi_id=vaschetta.id):
            return jsonify(error="Posizione non valida: fuori dal supporto o in collisione con un'altra vaschetta."), 400

        vaschetta.x = x
        vaschetta.y = y
        vaschetta.ruotata = ruotata

    if "gruppo" in data:
        gruppo = data["gruppo"] or None
        if gruppo is not None:
            commessa_id = vaschetta.contenitore.commessa_id
            esiste = RigaCommessa.query.filter_by(commessa_id=commessa_id, gruppo=gruppo).first()
            if not esiste:
                return jsonify(error="Gruppo non trovato per questa commessa."), 400
        vaschetta.gruppo = gruppo

    db.session.commit()
    return jsonify(vaschetta.to_dict())


@bancale_bp.route("/contenitore/<int:contenitore_id>/stampa-etichette", methods=["POST"])
def stampa_etichette_gruppi(contenitore_id):
    contenitore = Contenitore.query.get_or_404(contenitore_id)

    gruppi = {v.gruppo for v in contenitore.vaschette if v.gruppo}
    if not gruppi:
        return jsonify(error="Nessun gruppo assegnato su questo supporto."), 400

    righe = RigaCommessa.query.filter(
        RigaCommessa.commessa_id == contenitore.commessa_id,
        RigaCommessa.gruppo.in_(gruppi),
    ).all()

    data = [(r.codice, r.descrizione or "") for r in righe if r.codice]
    if not data:
        return jsonify(error="Nessun articolo trovato per i gruppi assegnati."), 400

    job_id = create_job()
    run_in_background(job_id, label_jobs.process_barcode_from_data, data, job_id)
    return jsonify(job_id=job_id)


@bancale_bp.route("/<int:commessa_id>/stampa-cartello", methods=["POST"])
def stampa_cartello(commessa_id):
    commessa = Commessa.query.get_or_404(commessa_id)
    data = request.get_json(silent=True) or {}
    immagine = data.get("immagine")
    numero_bancale = (data.get("numero_bancale") or "").strip()

    if immagine not in cartello_job.NOMI_CARTELLI:
        return jsonify(error="Seleziona un'immagine valida."), 400
    if not numero_bancale:
        return jsonify(error="Il numero/nome del supporto è obbligatorio."), 400

    titolo = commessa.nome
    sottotitolo = f"Bancale N. {numero_bancale}"

    job_id = create_job()
    run_in_background(job_id, cartello_job.generate_cartello_pdf, immagine, titolo, sottotitolo, job_id)
    return jsonify(job_id=job_id)


@bancale_bp.route("/job/<job_id>/status")
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify(error="Job non trovato."), 404
    payload = {"status": job["status"], "error": job.get("error")}
    if job["status"] == "done":
        payload["download_url"] = url_for("bancale.job_download", job_id=job_id)
    return jsonify(payload)


@bancale_bp.route("/job/<job_id>/download")
def job_download(job_id):
    job = get_job(job_id)
    if not job or job["status"] != "done" or not job.get("output_path"):
        return "PDF non disponibile.", 404
    return send_file(job["output_path"], mimetype="application/pdf", download_name=f"bancale_{job_id}.pdf")
