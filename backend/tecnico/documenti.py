import re
from datetime import datetime

from flask import render_template, redirect, url_for, request, flash, session

from core.auth import session_check
from core.db import db
from models.panthera_order import PantheraOrder
from models.service_document import ServiceDocument, ServiceDocumentMaterial
from tecnico import tecnico_bp

_COMMESSA_RE = re.compile(r'^[A-Z]{2,4}\s\d{6}$')


@tecnico_bp.route('/documenti')
@session_check('tecnico')
def documenti():
    uid   = session['user_id']
    lista = (ServiceDocument.query
             .filter_by(tecnico_user_id=uid)
             .order_by(ServiceDocument.created_at.desc())
             .all())
    return render_template('tecnico/documenti.html', title='Documenti Servizio', documenti=lista)


@tecnico_bp.route('/documenti/nuovo', methods=['POST'])
@session_check('tecnico')
def documento_nuovo():
    uid      = session['user_id']
    commessa = request.form.get('commessa', '').strip().upper()
    if commessa and not _COMMESSA_RE.match(commessa):
        flash('Formato commessa non valido (es. EX 000345)', 'error')
        return redirect(url_for('tecnico.documenti'))
    doc = ServiceDocument(
        tecnico_user_id   = uid,
        panthera_order_id = request.form.get('panthera_order_id') or None,
        van_id            = request.form.get('van_id') or None,
        description       = request.form.get('description', '').strip(),
        commessa          = commessa or None,
        status            = 'open',
    )
    db.session.add(doc)
    db.session.commit()
    flash('Documento creato.', 'success')
    return redirect(url_for('tecnico.documenti'))


@tecnico_bp.route('/documenti/<int:doc_id>')
@session_check('tecnico')
def documento_dettaglio(doc_id):
    uid       = session['user_id']
    doc       = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    materiali = doc.materials
    ordini    = PantheraOrder.query.filter_by(assigned_user_id=uid).all()
    return render_template('tecnico/documento_dettaglio.html', title='Documento',
                           doc=doc, materiali=materiali, ordini=ordini)


@tecnico_bp.route('/documenti/<int:doc_id>/materiale', methods=['POST'])
@session_check('tecnico')
def materiale_aggiungi(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()

    if doc.status != 'open':
        flash('Documento non modificabile.', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))

    mat = ServiceDocumentMaterial(
        service_document_id = doc_id,
        part_code           = request.form.get('part_code', '').strip().upper(),
        description         = request.form.get('description', '').strip(),
        quantity_used       = int(request.form.get('quantity_used', 1)),
    )
    db.session.add(mat)
    db.session.commit()
    flash('Materiale aggiunto.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/<int:doc_id>/materiale/<int:mat_id>/elimina', methods=['POST'])
@session_check('tecnico')
def materiale_elimina(doc_id, mat_id):
    uid = session['user_id']
    ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    mat = db.get_or_404(ServiceDocumentMaterial, mat_id)
    db.session.delete(mat)
    db.session.commit()
    flash('Materiale rimosso.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/<int:doc_id>/chiudi', methods=['POST'])
@session_check('tecnico')
def documento_chiudi(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    doc.status    = 'closed'
    doc.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Documento chiuso.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/<int:doc_id>/commessa', methods=['POST'])
@session_check('tecnico')
def documento_aggiorna_commessa(doc_id):
    uid      = session['user_id']
    doc      = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    commessa = request.form.get('commessa', '').strip().upper()
    if commessa and not _COMMESSA_RE.match(commessa):
        flash('Formato commessa non valido (es. EX 000345)', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))
    doc.commessa = commessa or None
    db.session.commit()
    flash('Commessa aggiornata.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/bulk-close', methods=['POST'])
@session_check('tecnico')
def documenti_bulk_close():
    uid     = session['user_id']
    ids_raw = request.form.getlist('ids[]')
    if not ids_raw:
        flash('Nessun documento selezionato.', 'error')
        return redirect(url_for('tecnico.documenti'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = ServiceDocument.query.filter(
        ServiceDocument.id.in_(ids),
        ServiceDocument.tecnico_user_id == uid,
        ServiceDocument.status == 'open'
    ).all()

    now = datetime.utcnow()
    for d in record:
        d.status    = 'closed'
        d.closed_at = now
    db.session.commit()
    flash(f'{len(record)} documenti chiusi.', 'success')
    return redirect(url_for('tecnico.documenti'))
