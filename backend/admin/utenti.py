from flask import render_template, redirect, url_for, request, flash, session

from core.auth import session_check
from core.db import db
from models.user import User
from admin import admin_bp


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
    utente           = db.get_or_404(User, utente_id)
    utente.is_active = not utente.is_active
    db.session.commit()
    stato = 'attivato' if utente.is_active else 'disattivato'
    flash(f'Utente {utente.username} {stato}.', 'success')
    return redirect(url_for('admin.utenti'))


@admin_bp.route('/utenti/<int:utente_id>/elimina', methods=['POST'])
@session_check('admin')
def utenti_elimina(utente_id):
    utente = db.get_or_404(User, utente_id)
    if utente.id == session.get('user_id'):
        flash('Non puoi eliminare il tuo account.', 'error')
        return redirect(url_for('admin.utenti'))

    n_ordini   = len(utente.orders)
    n_docs     = len(utente.service_documents)
    n_receipts = len(utente.receipts)

    if n_ordini + n_docs + n_receipts > 0:
        flash(
            f'Impossibile eliminare {utente.username}: '
            f'esistono {n_ordini} ordini, {n_docs} documenti e {n_receipts} scontrini associati. '
            f'Usa Disattiva per bloccare l\'accesso senza perdere i dati.',
            'error'
        )
        return redirect(url_for('admin.utenti'))

    db.session.delete(utente)
    db.session.commit()
    flash(f'Utente {utente.username} eliminato.', 'success')
    return redirect(url_for('admin.utenti'))


@admin_bp.route('/utenti/bulk-toggle', methods=['POST'])
@session_check('admin')
def utenti_bulk_toggle():
    ids_raw    = request.form.getlist('ids[]')
    current_id = session.get('user_id')
    if not ids_raw:
        flash('Nessun utente selezionato.', 'error')
        return redirect(url_for('admin.utenti'))

    ids    = [int(i) for i in ids_raw if i.isdigit() and int(i) != current_id]
    record = User.query.filter(User.id.in_(ids)).all()
    for u in record:
        u.is_active = not u.is_active
    db.session.commit()
    flash(f'{len(record)} utenti aggiornati.', 'success')
    return redirect(url_for('admin.utenti'))
