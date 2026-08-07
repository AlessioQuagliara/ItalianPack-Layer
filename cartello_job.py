from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
IMMAGINI_DIR = BASE_DIR / "cartelli_immagini"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PAGE_SIZE = landscape(A4)

NOMI_CARTELLI = [
    "PERSEUS",
    "ARGO",
    "OLYMPUS",
    "OLYMPUS-22",
    "OCEANIA",
    "OCEANIA-22",
    "OCEANIA-MINI",
    "OCEANIA-MINI-22",
    "ARTEMIS",
    "POSEIDON",
    "POSEIDON-JOLLY",
    "GASTRO",
    "DT1000",
    "OLYMPUS-XL",
    "POLARIS",
    "POLARIS-XL",
    "EXPRESS",
    "EXPRESS-XL"
]


def _wrap_by_width(text, font_name, font_size, max_width, canvas_obj):
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if canvas_obj.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def generate_cartello_pdf(nome, titolo, sottotitolo, job_id):
    if nome not in NOMI_CARTELLI:
        raise ValueError(f"Nome non valido: {nome}")

    titolo = (titolo or "").strip()
    if not titolo:
        raise ValueError("Il titolo è obbligatorio.")

    sottotitolo = (sottotitolo or "").strip()

    image_path = IMMAGINI_DIR / f"{nome}.png"
    if not image_path.is_file():
        raise ValueError(
            f"Immagine non trovata per '{nome}'. Aggiungi il file {nome}.png nella cartella cartelli_immagini."
        )

    output_path = OUTPUT_DIR / f"{job_id}.pdf"

    page_width, page_height = PAGE_SIZE
    margin = 20 * mm
    usable_width = page_width - 2 * margin

    c = canvas.Canvas(str(output_path), pagesize=PAGE_SIZE)

    img_reader = ImageReader(str(image_path))
    img_w, img_h = img_reader.getSize()
    max_img_w = usable_width
    max_img_h = page_height * 0.55
    scale = min(max_img_w / img_w, max_img_h / img_h)
    draw_w, draw_h = img_w * scale, img_h * scale
    img_x = margin + (usable_width - draw_w) / 2
    img_y = page_height - margin - draw_h
    c.drawImage(
        img_reader,
        img_x,
        img_y,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True,
        mask="auto",
    )

    current_y = img_y - 16 * mm

    title_font = "Helvetica-Bold"
    title_size = 40
    c.setFont(title_font, title_size)
    for line in _wrap_by_width(titolo, title_font, title_size, usable_width, c):
        line_width = c.stringWidth(line, title_font, title_size)
        c.drawString(margin + (usable_width - line_width) / 2, current_y, line)
        current_y -= title_size * 1.15

    if sottotitolo:
        current_y -= 8 * mm
        sub_font = "Helvetica"
        sub_size = 22
        c.setFont(sub_font, sub_size)
        for line in _wrap_by_width(sottotitolo, sub_font, sub_size, usable_width, c):
            line_width = c.stringWidth(line, sub_font, sub_size)
            c.drawString(margin + (usable_width - line_width) / 2, current_y, line)
            current_y -= sub_size * 1.25

    c.save()
    return output_path
