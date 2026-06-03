from flask import render_template, request, redirect, url_for, flash

from core.auth import session_check
from core.db import db
from models.panthera_order import PantheraOrder
from models.user import User
from models.van import Van
from admin import admin_bp

STATI_ORDINE = ('pending', 'in_progress', 'completed', 'cancelled')


@admin_bp.route('/ordini')
@session_check('admin')
def ordini():
    filtro_stato = request.args.get('status', '')
    page         = request.args.get('page', 1, type=int)
    query        = PantheraOrder.query.order_by(PantheraOrder.created_at.desc())
    if filtro_stato:
        query = query.filter_by(status=filtro_stato)
    paginazione = query.paginate(page=page, per_page=50, error_out=False)
    tecnici     = User.query.filter_by(role='tecnico', is_active=True).order_by(User.username).all()
    furgoni     = Van.query.filter_by(is_active=True).order_by(Van.code).all()
    return render_template('responsabile/ordini.html', title='Ordini',
                           ordini=paginazione.items, filtro_stato=filtro_stato,
                           paginazione=paginazione, tecnici=tecnici, furgoni=furgoni)


@admin_bp.route('/ordini/bulk-update', methods=['POST'])
@session_check('admin')
def ordini_bulk_update():
    ids_raw = request.form.getlist('ids[]')
    field   = request.form.get('field', '')
    value   = request.form.get('value', '')

    CAMPI_VALIDI = {'status', 'assigned_user_id', 'van_id'}
    if not ids_raw or field not in CAMPI_VALIDI:
        flash('Dati non validi.', 'error')
        return redirect(url_for('admin.ordini'))

    ids    = [int(i) for i in ids_raw if i.isdigit()]
    record = PantheraOrder.query.filter(PantheraOrder.id.in_(ids)).all()

    for o in record:
        if field == 'status':
            if value in STATI_ORDINE:
                o.status = value
        elif field == 'assigned_user_id':
            o.assigned_user_id = int(value) if value and value.isdigit() else None
        elif field == 'van_id':
            o.van_id = int(value) if value and value.isdigit() else None

    db.session.commit()
    flash(f'{len(record)} ordini aggiornati.', 'success')
    return redirect(url_for('admin.ordini'))
