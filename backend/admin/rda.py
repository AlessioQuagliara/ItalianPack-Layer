from flask import render_template, request, redirect, url_for, flash

from core.auth import session_check
from core.db import db
from models.reintegration_request import ReintegrationRequest
from admin import admin_bp

STATI_RDA = ('pending', 'in_preparation', 'ready', 'delivered')


@admin_bp.route('/rda')
@session_check('admin')
def rda():
    lista = ReintegrationRequest.query.order_by(
        ReintegrationRequest.is_urgent.desc(),
        ReintegrationRequest.created_at.desc()
    ).all()
    return render_template('responsabile/rda.html', title='RDA – Reintegro',
                           rda_list=lista, stati=STATI_RDA)


@admin_bp.route('/rda/bulk-update', methods=['POST'])
@session_check('admin')
def rda_bulk_update():
    ids_raw = request.form.getlist('ids[]')
    status  = request.form.get('status', '')

    if not ids_raw or status not in STATI_RDA:
        flash('Dati non validi.', 'error')
        return redirect(url_for('admin.rda'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = ReintegrationRequest.query.filter(ReintegrationRequest.id.in_(ids)).all()
    for r in record:
        r.status = status
    db.session.commit()
    flash(f'{len(record)} RDA aggiornate a "{status}".', 'success')
    return redirect(url_for('admin.rda'))
