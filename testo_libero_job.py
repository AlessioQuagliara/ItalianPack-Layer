from pathlib import Path

from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

QUANTITA_MIN, QUANTITA_MAX = 1, 500
FONT_SIZE_MIN, FONT_SIZE_MAX = 6, 80
TESTO_MAX_LEN = 200

PAGE_WIDTH_MM = 70
PAGE_HEIGHT_MM = 27


def generate_testo_pdf(testo, quantita, font_size, orientamento, job_id):
    testo = (testo or "").strip()
    if not testo:
        raise ValueError("Il testo da stampare è obbligatorio.")
    if len(testo) > TESTO_MAX_LEN:
        raise ValueError(f"Il testo non può superare {TESTO_MAX_LEN} caratteri.")

    quantita = int(quantita)
    if not (QUANTITA_MIN <= quantita <= QUANTITA_MAX):
        raise ValueError(f"La quantità deve essere tra {QUANTITA_MIN} e {QUANTITA_MAX}.")

    font_size = float(font_size)
    if not (FONT_SIZE_MIN <= font_size <= FONT_SIZE_MAX):
        raise ValueError(f"La dimensione del carattere deve essere tra {FONT_SIZE_MIN} e {FONT_SIZE_MAX}.")

    if orientamento not in ("orizzontale", "verticale"):
        raise ValueError("Orientamento non valido.")

    output_path = OUTPUT_DIR / f"{job_id}.pdf"
    page_width_pt = PAGE_WIDTH_MM * mm
    page_height_pt = PAGE_HEIGHT_MM * mm

    c = canvas.Canvas(str(output_path), pagesize=(page_width_pt, page_height_pt))
    font_name = "Helvetica"
    c.setFont(font_name, font_size)
    text_width = c.stringWidth(testo, font_name, font_size)

    available_pt = page_height_pt if orientamento == "verticale" else page_width_pt
    if text_width > available_pt:
        raise ValueError(
            "Il testo non entra nell'etichetta con queste impostazioni. "
            "Riduci il testo o la dimensione del carattere."
        )

    for idx in range(quantita):
        if idx > 0:
            c.showPage()
            c.setFont(font_name, font_size)

        if orientamento == "verticale":
            c.saveState()
            c.translate(page_width_pt / 2, page_height_pt / 2)
            c.rotate(90)
            c.drawString(-text_width / 2, -font_size * 0.35, testo)
            c.restoreState()
        else:
            text_x = (page_width_pt - text_width) / 2
            text_y = (page_height_pt / 2) - (font_size * 0.35)
            c.drawString(text_x, text_y, testo)

    c.save()
    return output_path
