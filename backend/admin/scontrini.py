from flask import render_template, redirect, url_for, request, flash

from core.auth import session_check
from core.db import db
from models.receipt import Receipt
from admin import admin_bp


@admin_bp.route('/scontrini')
@session_check('admin')
def scontrini():
    lista = Receipt.query.order_by(Receipt.created_at.desc()).all()
    return render_template('responsabile/scontrini.html', title='Scontrini', scontrini=lista)


@admin_bp.route('/scontrini/<int:scontrino_id>/valida', methods=['POST'])
@session_check('admin')
def scontrino_valida(scontrino_id):
    scontrino        = db.get_or_404(Receipt, scontrino_id)
    scontrino.status = 'validated'
    db.session.commit()
    flash('Scontrino validato.', 'success')
    return redirect(url_for('admin.scontrini'))


@admin_bp.route('/scontrini/<int:scontrino_id>/rifiuta', methods=['POST'])
@session_check('admin')
def scontrino_rifiuta(scontrino_id):
    scontrino        = db.get_or_404(Receipt, scontrino_id)
    scontrino.status = 'rejected'
    scontrino.notes  = request.form.get('note', '')
    db.session.commit()
    flash('Scontrino rifiutato.', 'success')
    return redirect(url_for('admin.scontrini'))
