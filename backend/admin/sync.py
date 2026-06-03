from flask import render_template, redirect, url_for, flash, current_app

from core.auth import session_check
from models.panthera_sync_log import PantheraSyncLog
from services.panthera_service import PantheraService
from admin import admin_bp


@admin_bp.route('/log-sync')
@session_check('admin')
def log_sync():
    lista = PantheraSyncLog.query.order_by(PantheraSyncLog.created_at.desc()).limit(100).all()
    return render_template('responsabile/log_sync.html', title='Log Sincronizzazione', logs=lista)


@admin_bp.route('/sync-panthera', methods=['POST'])
@session_check('admin')
def sync_panthera():
    if not current_app.config.get('PANTHERA_BASE_URL'):
        flash('PANTHERA_BASE_URL non configurato.', 'error')
        return redirect(url_for('admin.log_sync'))

    try:
        log = PantheraService().sync_ordini()
        flash(f'Sync completato: {log.ordini_importati} nuovi, '
              f'{log.ordini_aggiornati} aggiornati, {log.errori} errori.', 'success')
    except Exception as e:
        flash(f'Errore sync: {e}', 'error')

    return redirect(url_for('admin.log_sync'))
