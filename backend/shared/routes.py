# shared/routes.py
from flask import request, redirect, url_for, flash, session

from shared import shared_bp
from models.service_document import ServiceDocument

_ROLE_DASHBOARDS = {
    'admin':     'admin.dashboard',
    'magazzino': 'magazzino.dashboard',
    'tecnico':   'tecnico.dashboard',
}

_ROLE_DOC_LIST = {
    'admin':     lambda commessa: url_for('admin.documenti', commessa=commessa),
    'magazzino': lambda commessa: url_for('magazzino.analisi', commessa=commessa),
}


@shared_bp.route('/search')
def search():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    commessa = request.args.get('commessa', '').strip().upper()
    role     = request.args.get('role', session.get('role', 'admin'))

    if not commessa:
        return redirect(url_for(_ROLE_DASHBOARDS.get(role, 'auth.login')))

    risultati = (ServiceDocument.query
                 .filter(ServiceDocument.commessa.ilike(f'%{commessa}%'))
                 .all())

    if not risultati:
        flash(f'Nessun documento trovato per commessa "{commessa}".', 'warning')
        fallback = url_for(_ROLE_DASHBOARDS.get(role, 'auth.login'))
        return redirect(request.referrer or fallback)

    dest_fn = _ROLE_DOC_LIST.get(role)
    if dest_fn:
        return redirect(dest_fn(commessa))

    # Fallback: admin documenti
    return redirect(url_for('admin.documenti', commessa=commessa))
