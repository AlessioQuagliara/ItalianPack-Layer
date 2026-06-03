import os

from flask import render_template, redirect, url_for, request, flash, current_app, send_from_directory

from core.auth import session_check
from core.db import db
from models.receipt import Receipt
from admin import admin_bp


@admin_bp.route('/scontrini')
@session_check('admin')
def scontrini():
    lista = Receipt.query.order_by(Receipt.created_at.desc()).all()
    return render_template('responsabile/scontrini.html', title='Scontrini', scontrini=lista)


@admin_bp.route('/scontrini/<int:scontrino_id>/view')
@session_check('admin')
def scontrino_view(scontrino_id):
    scontrino = db.get_or_404(Receipt, scontrino_id)
    cartella  = os.path.abspath(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
    return send_from_directory(cartella, scontrino.filename, as_attachment=False)


@admin_bp.route('/scontrini/<int:scontrino_id>/valida', methods=['POST'])
@session_check('admin')
def scontrino_valida(scontrino_id):
    scontrino        = db.get_or_404(Receipt, scontrino_id)
    scontrino.status = 'validated'
    db.session.commit()
    flash('Scontrino validato.', 'success')
    return redirect(url_for('admin.scontrini'))


@admin_bp.route('/scontrini/<int:scontrino_id>/rifiuta', methods=['POST'])
@session_check('admin')
def scontrino_rifiuta(scontrino_id):
    scontrino        = db.get_or_404(Receipt, scontrino_id)
    scontrino.status = 'rejected'
    scontrino.notes  = request.form.get('note', '')
    db.session.commit()
    flash('Scontrino rifiutato.', 'success')
    return redirect(url_for('admin.scontrini'))


@admin_bp.route('/scontrini/bulk-validate', methods=['POST'])
@session_check('admin')
def scontrini_bulk_validate():
    ids_raw = request.form.getlist('ids[]')
    if not ids_raw:
        flash('Nessuno scontrino selezionato.', 'error')
        return redirect(url_for('admin.scontrini'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = Receipt.query.filter(
        Receipt.id.in_(ids),
        Receipt.status == 'ocr_done'
    ).all()
    for s in record:
        s.status = 'validated'
    db.session.commit()
    flash(f'{len(record)} scontrini validati.', 'success')
    return redirect(url_for('admin.scontrini'))


@admin_bp.route('/scontrini/bulk-reject', methods=['POST'])
@session_check('admin')
def scontrini_bulk_reject():
    ids_raw = request.form.getlist('ids[]')
    note    = request.form.get('note', '').strip()
    if not ids_raw:
        flash('Nessuno scontrino selezionato.', 'error')
        return redirect(url_for('admin.scontrini'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = Receipt.query.filter(
        Receipt.id.in_(ids),
        Receipt.status == 'ocr_done'
    ).all()
    for s in record:
        s.status = 'rejected'
        if note:
            s.notes = note
    db.session.commit()
    flash(f'{len(record)} scontrini rifiutati.', 'success')
    return redirect(url_for('admin.scontrini'))
