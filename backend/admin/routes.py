# admin/routes.py
# Blueprint per il ruolo "admin" (ex after_sales responsabile)
from flask import render_template, redirect, url_for, request, flash, Blueprint

from core.auth import session_check
from core.db import db
from models.user import User
from models.panthera_order import PantheraOrder
from models.service_document import ServiceDocument
from models.reintegration_request import ReintegrationRequest
from models.receipt import Receipt
from models.panthera_sync_log import PantheraSyncLog
from models.van import Van

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@admin_bp.route('/dashboard')
@session_check('admin')
def dashboard():
    conteggi = {
        'ordini_aperti':   PantheraOrder.query.filter_by(status='pending').count(),
        'rda_in_sospeso':  ReintegrationRequest.query.filter_by(status='pending').count(),
        'scontrini_ocr':   Receipt.query.filter_by(status='pending_ocr').count(),
        'utenti_attivi':   User.query.filter_by(is_active=True).count(),
    }
    ultimi_log = PantheraSyncLog.query.order_by(PantheraSyncLog.created_at.desc()).limit(5).all()
    return render_template('responsabile/dashboard.html',
                           title='Dashboard', conteggi=conteggi, ultimi_log=ultimi_log)


# ------------------------------------------------------------------
# Gestione utenti
# ------------------------------------------------------------------

@admin_bp.route('/utenti')
@session_check('admin')
def utenti():
    lista = User.query.order_by(User.username).all()
    return render_template('responsabile/utenti.html', title='Utenti', utenti=lista)


@admin_bp.route('/utenti/nuovo', methods=['POST'])
@session_check('admin')
def utenti_nuovo():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    ruolo    = request.form.get('role', '')

    if not username or not password or ruolo not in ('admin', 'tecnico', 'magazzino'):
        flash('Dati non validi.', 'error')
        return redirect(url_for('admin.utenti'))

    if User.query.filter_by(username=username).first():
        flash('Username già in uso.', 'error')
        return redirect(url_for('admin.utenti'))

    utente = User(username=username, role=ruolo)
    utente.set_password(password)
    db.session.add(utente)
    db.session.commit()
    flash(f'Utente {username} creato.', 'success')
    return redirect(url_for('admin.utenti'))


@admin_bp.route('/utenti/<int:utente_id>/toggle', methods=['POST'])
@session_check('admin')
def utenti_toggle(utente_id):
    utente = User.query.get_or_404(utente_id)
    utente.is_active = not utente.is_active
    db.session.commit()
    stato = 'attivato' if utente.is_active else 'disattivato'
    flash(f'Utente {utente.username} {stato}.', 'success')
    return redirect(url_for('admin.utenti'))


@admin_bp.route('/utenti/<int:utente_id>/elimina', methods=['POST'])
@session_check('admin')
def utenti_elimina(utente_id):
    utente = User.query.get_or_404(utente_id)
    db.session.delete(utente)
    db.session.commit()
    flash('Utente eliminato.', 'success')
    return redirect(url_for('admin.utenti'))


# ------------------------------------------------------------------
# Ordini Panthera
# ------------------------------------------------------------------

@admin_bp.route('/ordini')
@session_check('admin')
def ordini():
    filtro_stato = request.args.get('status', '')
    query = PantheraOrder.query.order_by(PantheraOrder.created_at.desc())
    if filtro_stato:
        query = query.filter_by(status=filtro_stato)
    lista = query.all()
    return render_template('responsabile/ordini.html', title='Ordini', ordini=lista,
                           filtro_stato=filtro_stato)


# ------------------------------------------------------------------
# Documenti di servizio
# ------------------------------------------------------------------

@admin_bp.route('/documenti')
@session_check('admin')
def documenti():
    lista = ServiceDocument.query.order_by(ServiceDocument.created_at.desc()).all()
    return render_template('responsabile/documenti.html', title='Documenti di Servizio',
                           documenti=lista)


# ------------------------------------------------------------------
# RDA (Richieste di Reintegro)
# ------------------------------------------------------------------

@admin_bp.route('/rda')
@session_check('admin')
def rda():
    lista = ReintegrationRequest.query.order_by(
        ReintegrationRequest.is_urgent.desc(),
        ReintegrationRequest.created_at.desc()
    ).all()
    return render_template('responsabile/rda.html', title='RDA – Reintegro', rda_list=lista)


# ------------------------------------------------------------------
# Scontrini
# ------------------------------------------------------------------

@admin_bp.route('/scontrini')
@session_check('admin')
def scontrini():
    lista = Receipt.query.order_by(Receipt.created_at.desc()).all()
    return render_template('responsabile/scontrini.html', title='Scontrini', scontrini=lista)


@admin_bp.route('/scontrini/<int:scontrino_id>/valida', methods=['POST'])
@session_check('admin')
def scontrino_valida(scontrino_id):
    scontrino = Receipt.query.get_or_404(scontrino_id)
    scontrino.status = 'validated'
    db.session.commit()
    flash('Scontrino validato.', 'success')
    return redirect(url_for('admin.scontrini'))


@admin_bp.route('/scontrini/<int:scontrino_id>/rifiuta', methods=['POST'])
@session_check('admin')
def scontrino_rifiuta(scontrino_id):
    scontrino = Receipt.query.get_or_404(scontrino_id)
    scontrino.status = 'rejected'
    scontrino.notes  = request.form.get('note', '')
    db.session.commit()
    flash('Scontrino rifiutato.', 'success')
    return redirect(url_for('admin.scontrini'))


# ------------------------------------------------------------------
# Log sincronizzazione Panthera
# ------------------------------------------------------------------

@admin_bp.route('/log-sync')
@session_check('admin')
def log_sync():
    lista = PantheraSyncLog.query.order_by(PantheraSyncLog.created_at.desc()).limit(100).all()
    return render_template('responsabile/log_sync.html', title='Log Sincronizzazione', logs=lista)


@admin_bp.route('/sync-panthera', methods=['POST'])
@session_check('admin')
def sync_panthera():
    """Avvia una sincronizzazione manuale con Panthera ERP."""
    from flask import current_app
    from services.panthera_service import PantheraService

    if not current_app.config.get('PANTHERA_BASE_URL'):
        flash('PANTHERA_BASE_URL non configurato.', 'error')
        return redirect(url_for('admin.log_sync'))

    try:
        svc = PantheraService()
        log = svc.sync_ordini()
        flash(f'Sync completato: {log.ordini_importati} nuovi, '
              f'{log.ordini_aggiornati} aggiornati, {log.errori} errori.', 'success')
    except Exception as e:
        flash(f'Errore sync: {e}', 'error')

    return redirect(url_for('admin.log_sync'))
