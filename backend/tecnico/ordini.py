from flask import render_template, session

from core.auth import session_check
from models.panthera_order import PantheraOrder
from models.service_document import ServiceDocument
from models.receipt import Receipt
from tecnico import tecnico_bp


@tecnico_bp.route('/dashboard')
@session_check('tecnico')
def dashboard():
    uid = session['user_id']
    conteggi = {
        'ordini_assegnati':   PantheraOrder.query.filter_by(assigned_user_id=uid, status='pending').count(),
        'documenti_aperti':   ServiceDocument.query.filter_by(tecnico_user_id=uid, status='open').count(),
        'scontrini_pendenti': Receipt.query.filter_by(uploaded_by_user_id=uid, status='pending_ocr').count(),
    }
    ultimi_ordini = (PantheraOrder.query
                     .filter_by(assigned_user_id=uid)
                     .order_by(PantheraOrder.scheduled_date.asc())
                     .limit(5).all())
    return render_template('tecnico/dashboard.html', title='Dashboard',
                           conteggi=conteggi, ultimi_ordini=ultimi_ordini)


@tecnico_bp.route('/ordini')
@session_check('tecnico')
def ordini():
    uid   = session['user_id']
    lista = (PantheraOrder.query
             .filter_by(assigned_user_id=uid)
             .order_by(PantheraOrder.scheduled_date.asc())
             .all())
    return render_template('tecnico/ordini.html', title='I Miei Ordini', ordini=lista)
