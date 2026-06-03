import io
import re

import qrcode
from flask import render_template, redirect, url_for, request, flash, send_file
from sqlalchemy import func

from core.auth import session_check
from core.db import db
from models.van import Van
from models.panthera_order import PantheraOrder
from admin import admin_bp

_RE_CODE  = re.compile(r'^[A-Za-z0-9\-]{1,32}$')
_RE_TARGA = re.compile(r'^[A-Z]{2}\d{3}[A-Z]{2}$')


def _valida_codice(code: str) -> str | None:
    if not code:
        return 'Il codice è obbligatorio.'
    if not _RE_CODE.match(code):
        return 'Codice non valido: usa solo lettere, cifre e trattini (max 32 caratteri).'
    return None


def _valida_targa(plate: str) -> str | None:
    if not plate:
        return None
    if not _RE_TARGA.match(plate.upper()):
        return 'Targa non valida: usa il formato italiano (es. AA000AA).'
    return None


def _ordini_attivi_per_van() -> dict:
    rows = (
        db.session.query(PantheraOrder.van_id, func.count(PantheraOrder.id))
        .filter(
            PantheraOrder.van_id.isnot(None),
            PantheraOrder.status.in_(['pending', 'in_progress'])
        )
        .group_by(PantheraOrder.van_id)
        .all()
    )
    return {van_id: count for van_id, count in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Lista
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni')
@session_check('admin')
def furgoni():
    tutti    = Van.query.order_by(Van.code).all()
    attivi   = sum(1 for v in tutti if v.is_active)
    kpi      = {'totale': len(tutti), 'attivi': attivi, 'inattivi': len(tutti) - attivi}
    conteggi = _ordini_attivi_per_van()
    return render_template('responsabile/furgoni.html', title='Furgoni',
                           furgoni=tutti, kpi=kpi, ordini_attivi=conteggi)


# ─────────────────────────────────────────────────────────────────────────────
# QR code
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/<int:van_id>/qr')
@session_check('admin')
def furgoni_qr(van_id):
    van       = db.get_or_404(Van, van_id)
    base_url  = request.host_url.rstrip('/')
    target    = f"{base_url}/furgoni/{van.code}/materiali"

    qr_img = qrcode.make(target)
    buf    = io.BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ─────────────────────────────────────────────────────────────────────────────
# Crea
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/nuovo', methods=['POST'])
@session_check('admin')
def furgoni_nuovo():
    code  = request.form.get('code', '').strip()
    name  = request.form.get('name', '').strip()
    plate = request.form.get('plate_number', '').strip().upper() or None

    if err := _valida_codice(code):
        flash(err, 'error')
        return redirect(url_for('admin.furgoni'))
    if not name:
        flash('Il nome è obbligatorio.', 'error')
        return redirect(url_for('admin.furgoni'))
    if len(name) > 128:
        flash('Il nome supera i 128 caratteri.', 'error')
        return redirect(url_for('admin.furgoni'))
    if plate and (err := _valida_targa(plate)):
        flash(err, 'error')
        return redirect(url_for('admin.furgoni'))
    if Van.query.filter_by(code=code).first():
        flash(f'Codice "{code}" già in uso.', 'error')
        return redirect(url_for('admin.furgoni'))

    van = Van(code=code, name=name, plate_number=plate)
    db.session.add(van)
    db.session.commit()
    flash(f'Furgone {code} creato.', 'success')
    return redirect(url_for('admin.furgoni'))


# ─────────────────────────────────────────────────────────────────────────────
# Modifica
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/<int:van_id>/edit', methods=['POST'])
@session_check('admin')
def furgoni_edit(van_id):
    van   = db.get_or_404(Van, van_id)
    code  = request.form.get('code', '').strip()
    name  = request.form.get('name', '').strip()
    plate = request.form.get('plate_number', '').strip().upper() or None

    if err := _valida_codice(code):
        flash(err, 'error')
        return redirect(url_for('admin.furgoni'))
    if not name:
        flash('Il nome è obbligatorio.', 'error')
        return redirect(url_for('admin.furgoni'))
    if len(name) > 128:
        flash('Il nome supera i 128 caratteri.', 'error')
        return redirect(url_for('admin.furgoni'))
    if plate and (err := _valida_targa(plate)):
        flash(err, 'error')
        return redirect(url_for('admin.furgoni'))
    if Van.query.filter(Van.code == code, Van.id != van_id).first():
        flash(f'Codice "{code}" già in uso da un altro furgone.', 'error')
        return redirect(url_for('admin.furgoni'))

    van.code         = code
    van.name         = name
    van.plate_number = plate
    db.session.commit()
    flash(f'Furgone {code} aggiornato.', 'success')
    return redirect(url_for('admin.furgoni'))


# ─────────────────────────────────────────────────────────────────────────────
# Toggle attiva/disattiva
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/<int:van_id>/toggle', methods=['POST'])
@session_check('admin')
def furgoni_toggle(van_id):
    van           = db.get_or_404(Van, van_id)
    van.is_active = not van.is_active
    db.session.commit()
    stato = 'attivato' if van.is_active else 'disattivato'
    flash(f'Furgone {van.code} {stato}.', 'success')
    return redirect(url_for('admin.furgoni'))


# ─────────────────────────────────────────────────────────────────────────────
# Elimina
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/<int:van_id>/elimina', methods=['POST'])
@session_check('admin')
def furgoni_elimina(van_id):
    van      = db.get_or_404(Van, van_id)
    n_ordini = len(van.orders)
    n_docs   = len(van.service_documents)

    if n_ordini + n_docs > 0:
        flash(
            f'Impossibile eliminare {van.code}: '
            f'esistono {n_ordini} ordini e {n_docs} documenti associati.',
            'error'
        )
        return redirect(url_for('admin.furgoni'))

    db.session.delete(van)
    db.session.commit()
    flash(f'Furgone {van.code} eliminato.', 'success')
    return redirect(url_for('admin.furgoni'))


# ─────────────────────────────────────────────────────────────────────────────
# Bulk toggle
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/furgoni/bulk-toggle', methods=['POST'])
@session_check('admin')
def furgoni_bulk_toggle():
    ids_raw = request.form.getlist('ids[]')
    if not ids_raw:
        flash('Nessun furgone selezionato.', 'error')
        return redirect(url_for('admin.furgoni'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = Van.query.filter(Van.id.in_(ids)).all()
    for v in record:
        v.is_active = not v.is_active
    db.session.commit()
    flash(f'{len(record)} furgoni aggiornati.', 'success')
    return redirect(url_for('admin.furgoni'))
