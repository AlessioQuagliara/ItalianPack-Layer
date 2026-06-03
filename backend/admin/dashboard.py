from flask import render_template

from core.auth import session_check
from models.user import User
from models.panthera_order import PantheraOrder
from models.reintegration_request import ReintegrationRequest
from models.receipt import Receipt
from models.panthera_sync_log import PantheraSyncLog
from admin import admin_bp


@admin_bp.route('/dashboard')
@session_check('admin')
def dashboard():
    conteggi = {
        'ordini_aperti':  PantheraOrder.query.filter_by(status='pending').count(),
        'rda_in_sospeso': ReintegrationRequest.query.filter_by(status='pending').count(),
        'scontrini_ocr':  Receipt.query.filter_by(status='pending_ocr').count(),
        'utenti_attivi':  User.query.filter_by(is_active=True).count(),
    }
    ultimi_log = PantheraSyncLog.query.order_by(PantheraSyncLog.created_at.desc()).limit(5).all()
    return render_template('responsabile/dashboard.html',
                           title='Dashboard', conteggi=conteggi, ultimi_log=ultimi_log)
