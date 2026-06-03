from flask import render_template, request

from core.auth import session_check
from models.panthera_order import PantheraOrder
from admin import admin_bp


@admin_bp.route('/ordini')
@session_check('admin')
def ordini():
    filtro_stato = request.args.get('status', '')
    page         = request.args.get('page', 1, type=int)
    query        = PantheraOrder.query.order_by(PantheraOrder.created_at.desc())
    if filtro_stato:
        query = query.filter_by(status=filtro_stato)
    paginazione = query.paginate(page=page, per_page=50, error_out=False)
    return render_template('responsabile/ordini.html', title='Ordini',
                           ordini=paginazione.items, filtro_stato=filtro_stato,
                           paginazione=paginazione)
