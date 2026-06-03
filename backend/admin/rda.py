from flask import render_template

from core.auth import session_check
from models.reintegration_request import ReintegrationRequest
from admin import admin_bp


@admin_bp.route('/rda')
@session_check('admin')
def rda():
    lista = ReintegrationRequest.query.order_by(
        ReintegrationRequest.is_urgent.desc(),
        ReintegrationRequest.created_at.desc()
    ).all()
    return render_template('responsabile/rda.html', title='RDA – Reintegro', rda_list=lista)
