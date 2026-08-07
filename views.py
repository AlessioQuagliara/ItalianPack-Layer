from pathlib import Path

from flask import request, jsonify, send_file, url_for
from flask_admin import AdminIndexView, BaseView, expose
from werkzeug.utils import secure_filename

import cartello_job
import label_jobs
import testo_libero_job
from jobs import create_job, get_job, run_in_background

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}


class DashboardIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        tools = [
            {
                "title": "Etichette con Barcode",
                "endpoint": "etichette_barcode.index",
                "description": "Barcode Code39 + codice + descrizione. Colonne Excel: Codice, Descrizione.",
            },
            {
                "title": "Etichette senza Barcode",
                "endpoint": "etichette_no_barcode.index",
                "description": "Testo libero con quantità, dimensione carattere e orientamento a scelta.",
            },
            {
                "title": "Etichette Viti (Speciali)",
                "endpoint": "etichette_viti.index",
                "description": "Barcode + codice grande + descrizione. Colonne Excel: Barcode, Descrizione, Codice.",
            },
            {
                "title": "Cartelli A4",
                "endpoint": "cartelli.index",
                "description": "Cartello verticale A4 con immagine, titolo e sottotitolo a scelta.",
            },
        ]
        return self.render("admin/home.html", tools=tools)


class BaseJobView(BaseView):
    """Espone gli endpoint di polling/download condivisi da tutte le sezioni job-based."""

    @expose("/status/<job_id>")
    def status(self, job_id):
        job = get_job(job_id)
        if not job:
            return jsonify(error="Job non trovato."), 404

        payload = {"status": job["status"], "error": job.get("error")}
        if job["status"] == "done":
            payload["download_url"] = url_for(".download", job_id=job_id)
        return jsonify(payload)

    @expose("/download/<job_id>")
    def download(self, job_id):
        job = get_job(job_id)
        if not job or job["status"] != "done" or not job.get("output_path"):
            return "PDF non disponibile.", 404
        return send_file(
            job["output_path"],
            mimetype="application/pdf",
            download_name=f"{self.endpoint}_{job_id}.pdf",
        )


class BaseEtichetteView(BaseJobView):
    processor = None
    page_title = ""
    page_description = ""
    columns_help = ""

    @expose("/", methods=["GET"])
    def index(self):
        return self.render(
            "etichette/upload.html",
            page_title=self.page_title,
            page_description=self.page_description,
            columns_help=self.columns_help,
        )

    @expose("/upload", methods=["POST"])
    def upload(self):
        file = request.files.get("excel_file")
        if not file or file.filename == "":
            return jsonify(error="Nessun file selezionato."), 400

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify(error="Formato non valido. Carica un file .xlsx"), 400

        job_id = create_job()
        safe_name = secure_filename(file.filename) or "upload.xlsx"
        saved_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
        file.save(saved_path)

        run_in_background(job_id, self.processor, saved_path, job_id)
        return jsonify(job_id=job_id)


class EtichetteBarcodeView(BaseEtichetteView):
    processor = staticmethod(label_jobs.process_barcode)
    page_title = "Etichette con Barcode"
    page_description = "Genera etichette 70x27mm con barcode Code39, codice e descrizione."
    columns_help = "Colonne richieste nel file Excel (intestazioni nella prima riga): Codice, Descrizione."


class EtichetteNoBarcodeView(BaseJobView):
    page_title = "Etichette senza Barcode"
    page_description = "Genera etichette 70x27mm da testo libero: scegli quantità, dimensione carattere e orientamento."

    @expose("/", methods=["GET"])
    def index(self):
        return self.render(
            "etichette/no_barcode_form.html",
            page_title=self.page_title,
            page_description=self.page_description,
            quantita_min=testo_libero_job.QUANTITA_MIN,
            quantita_max=testo_libero_job.QUANTITA_MAX,
            font_size_min=testo_libero_job.FONT_SIZE_MIN,
            font_size_max=testo_libero_job.FONT_SIZE_MAX,
        )

    @expose("/genera", methods=["POST"])
    def genera(self):
        testo = (request.form.get("testo") or "").strip()
        orientamento = request.form.get("orientamento") or "orizzontale"

        if not testo:
            return jsonify(error="Il testo da stampare è obbligatorio."), 400
        if orientamento not in ("orizzontale", "verticale"):
            return jsonify(error="Orientamento non valido."), 400

        try:
            quantita = int(request.form.get("quantita", "1"))
            font_size = float(request.form.get("font_size", "14"))
        except ValueError:
            return jsonify(error="Quantità o dimensione carattere non validi."), 400

        if not (testo_libero_job.QUANTITA_MIN <= quantita <= testo_libero_job.QUANTITA_MAX):
            return jsonify(
                error=f"La quantità deve essere tra {testo_libero_job.QUANTITA_MIN} e {testo_libero_job.QUANTITA_MAX}."
            ), 400
        if not (testo_libero_job.FONT_SIZE_MIN <= font_size <= testo_libero_job.FONT_SIZE_MAX):
            return jsonify(
                error=f"La dimensione del carattere deve essere tra {testo_libero_job.FONT_SIZE_MIN} e {testo_libero_job.FONT_SIZE_MAX}."
            ), 400

        job_id = create_job()
        run_in_background(
            job_id, testo_libero_job.generate_testo_pdf, testo, quantita, font_size, orientamento, job_id
        )
        return jsonify(job_id=job_id)


class EtichetteVitiView(BaseEtichetteView):
    processor = staticmethod(label_jobs.process_viti)
    page_title = "Etichette Viti (Speciali)"
    page_description = "Genera etichette 70x27mm con barcode, codice display grande e descrizione."
    columns_help = "Colonne nel file Excel in ordine (la prima riga viene sempre saltata): 1 Barcode, 2 Descrizione, 3 Codice display."


class CartelloView(BaseJobView):
    @expose("/", methods=["GET"])
    def index(self):
        return self.render(
            "cartelli/upload.html",
            page_title="Cartelli A4",
            page_description="Genera un cartello A4 verticale con immagine, titolo e sottotitolo.",
            nomi=cartello_job.NOMI_CARTELLI,
        )

    @expose("/genera", methods=["POST"])
    def genera(self):
        nome = (request.form.get("nome") or "").strip()
        titolo = (request.form.get("titolo") or "").strip()
        sottotitolo = (request.form.get("sottotitolo") or "").strip()

        if nome not in cartello_job.NOMI_CARTELLI:
            return jsonify(error="Seleziona un modello valido dall'elenco."), 400
        if not titolo:
            return jsonify(error="Il titolo è obbligatorio."), 400

        job_id = create_job()
        run_in_background(job_id, cartello_job.generate_cartello_pdf, nome, titolo, sottotitolo, job_id)
        return jsonify(job_id=job_id)
