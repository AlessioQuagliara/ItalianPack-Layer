import re
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash

from core.auth import session_check
from core.db import db
from models.service_document import ServiceDocument
from admin import admin_bp

_COMMESSA_RE = re.compile(r'^[A-Z]{2,4}\s\d{6}$')


@admin_bp.route('/documenti')
@session_check('admin')
def documenti():
    filtro_commessa = request.args.get('commessa', '').strip()
    query = ServiceDocument.query.order_by(ServiceDocument.created_at.desc())
    if filtro_commessa:
        query = query.filter(ServiceDocument.commessa.ilike(f'%{filtro_commessa}%'))
    lista = query.all()
    return render_template('responsabile/documenti.html', title='Documenti di Servizio',
                           documenti=lista, filtro_commessa=filtro_commessa)


@admin_bp.route('/documenti/<int:doc_id>/commessa', methods=['POST'])
@session_check('admin')
def documento_aggiorna_commessa(doc_id):
    doc      = db.get_or_404(ServiceDocument, doc_id)
    commessa = request.form.get('commessa', '').strip().upper()
    if commessa and not _COMMESSA_RE.match(commessa):
        flash('Formato commessa non valido (es. EX 000345)', 'error')
        return redirect(url_for('admin.documenti'))
    doc.commessa = commessa or None
    db.session.commit()
    flash('Commessa aggiornata.', 'success')
    return redirect(url_for('admin.documenti'))


@admin_bp.route('/documenti/bulk-close', methods=['POST'])
@session_check('admin')
def documenti_bulk_close():
    ids_raw = request.form.getlist('ids[]')
    if not ids_raw:
        flash('Nessun documento selezionato.', 'error')
        return redirect(url_for('admin.documenti'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = ServiceDocument.query.filter(
        ServiceDocument.id.in_(ids),
        ServiceDocument.status == 'open'
    ).all()

    now = datetime.utcnow()
    for d in record:
        d.status    = 'closed'
        d.closed_at = now
    db.session.commit()
    flash(f'{len(record)} documenti chiusi.', 'success')
    return redirect(url_for('admin.documenti'))
