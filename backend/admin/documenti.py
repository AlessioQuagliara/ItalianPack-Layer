from flask import render_template

from core.auth import session_check
from models.service_document import ServiceDocument
from admin import admin_bp


@admin_bp.route('/documenti')
@session_check('admin')
def documenti():
    lista = ServiceDocument.query.order_by(ServiceDocument.created_at.desc()).all()
    return render_template('responsabile/documenti.html', title='Documenti di Servizio',
                           documenti=lista)
