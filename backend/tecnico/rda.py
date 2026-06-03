from flask import redirect, url_for, request, flash, session

from core.auth import session_check
from core.db import db
from models.service_document import ServiceDocument
from services.document_service import crea_rda_da_documento
from tecnico import tecnico_bp


@tecnico_bp.route('/documenti/<int:doc_id>/richiedi-rda', methods=['POST'])
@session_check('tecnico')
def richiedi_rda(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()

    try:
        crea_rda_da_documento(
            doc     = doc,
            uid     = uid,
            urgente = bool(request.form.get('urgente')),
            note    = request.form.get('note', '').strip(),
        )
        db.session.commit()
        flash('RDA inviata al magazzino.', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))
