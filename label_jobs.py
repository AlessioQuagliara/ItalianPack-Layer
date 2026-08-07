import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from script import stampa_etichette
from script import stampa_etichette_viti

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def _ensure_data(data):
    if not data:
        raise ValueError("Il file Excel non contiene righe valide da stampare.")
    return data


def process_barcode(excel_path, job_id):
    data = _ensure_data(stampa_etichette.read_excel_data(str(excel_path)))
    output_path = OUTPUT_DIR / f"{job_id}.pdf"
    stampa_etichette.generate_pdf(data, output_filename=str(output_path))
    return output_path


def process_barcode_from_data(data, job_id):
    """Come process_barcode, ma parte da una lista (codice, descrizione) già pronta
    invece che da un file Excel — riusata dalla stampa etichette-gruppi del bancale."""
    data = _ensure_data(data)
    output_path = OUTPUT_DIR / f"{job_id}.pdf"
    stampa_etichette.generate_pdf(data, output_filename=str(output_path))
    return output_path


def process_viti(excel_path, job_id):
    data = _ensure_data(stampa_etichette_viti.read_excel_data(str(excel_path)))
    output_path = OUTPUT_DIR / f"{job_id}.pdf"
    stampa_etichette_viti.generate_pdf(data, output_filename=str(output_path))
    return output_path
