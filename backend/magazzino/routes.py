# magazzino/routes.py
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash

from core.auth import session_check
from core.db import db
from models.reintegration_request import ReintegrationRequest, ReintegrationRequestItem
from models.panthera_order import PantheraOrder
from magazzino import magazzino_bp

STATI_RDA_VALIDI = ('pending', 'in_preparation', 'ready', 'delivered')


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@magazzino_bp.route('/dashboard')
@session_check('magazzino')
def dashboard():
    conteggi = {
        'rda_pending':        ReintegrationRequest.query.filter_by(status='pending').count(),
        'rda_in_prep':        ReintegrationRequest.query.filter_by(status='in_preparation').count(),
        'rda_urgenti':        ReintegrationRequest.query.filter_by(is_urgent=True, status='pending').count(),
        'ordini_in_corso':    PantheraOrder.query.filter_by(status='in_progress').count(),
    }
    rda_urgenti = (ReintegrationRequest.query
                   .filter_by(is_urgent=True)
                   .filter(ReintegrationRequest.status.in_(['pending', 'in_preparation']))
                   .order_by(ReintegrationRequest.created_at.asc())
                   .limit(5).all())
    return render_template('magazzino/dashboard.html', title='Dashboard',
                           conteggi=conteggi, rda_urgenti=rda_urgenti)


# ------------------------------------------------------------------
# Lista RDA
# ------------------------------------------------------------------

@magazzino_bp.route('/rda')
@session_check('magazzino')
def rda():
    filtro = request.args.get('status', '')
    query  = ReintegrationRequest.query.order_by(
        ReintegrationRequest.is_urgent.desc(),
        ReintegrationRequest.created_at.asc()
    )
    if filtro and filtro in STATI_RDA_VALIDI:
        query = query.filter_by(status=filtro)
    lista = query.all()
    return render_template('magazzino/rda.html', title='RDA – Reintegro',
                           rda_list=lista, filtro=filtro, stati=STATI_RDA_VALIDI)


@magazzino_bp.route('/rda/<int:rda_id>')
@session_check('magazzino')
def rda_dettaglio(rda_id):
    rda   = db.get_or_404(ReintegrationRequest, rda_id)
    items = rda.items
    return render_template('magazzino/rda_dettaglio.html', title=f'RDA #{rda_id}',
                           rda=rda, items=items)


@magazzino_bp.route('/rda/<int:rda_id>/stato', methods=['POST'])
@session_check('magazzino')
def rda_aggiorna_stato(rda_id):
    rda    = db.get_or_404(ReintegrationRequest, rda_id)
    nuovo  = request.form.get('status', '')
    if nuovo not in STATI_RDA_VALIDI:
        flash('Stato non valido.', 'error')
    else:
        rda.status = nuovo
        db.session.commit()
        flash(f'RDA #{rda_id} aggiornata: {nuovo}.', 'success')
    return redirect(url_for('magazzino.rda_dettaglio', rda_id=rda_id))


@magazzino_bp.route('/rda/bulk-stato', methods=['POST'])
@session_check('magazzino')
def rda_bulk_stato():
    """Aggiorna lo stato di più RDA in una sola operazione."""
    ids_raw = request.form.getlist('rda_ids')
    nuovo   = request.form.get('status', '')

    if not ids_raw or nuovo not in STATI_RDA_VALIDI:
        flash('Dati non validi per l\'operazione bulk.', 'error')
        return redirect(url_for('magazzino.rda'))

    ids = [int(i) for i in ids_raw if i.isdigit()]
    aggiornate = ReintegrationRequest.query.filter(ReintegrationRequest.id.in_(ids)).all()
    for r in aggiornate:
        r.status = nuovo
    db.session.commit()
    flash(f'{len(aggiornate)} RDA aggiornate a "{nuovo}".', 'success')
    return redirect(url_for('magazzino.rda'))


# ------------------------------------------------------------------
# Aggiornamento item singolo (pezzi mancanti, arrivo previsto)
# ------------------------------------------------------------------

@magazzino_bp.route('/rda/<int:rda_id>/item/<int:item_id>', methods=['POST'])
@session_check('magazzino')
def rda_item_aggiorna(rda_id, item_id):
    db.get_or_404(ReintegrationRequest, rda_id)
    item = db.get_or_404(ReintegrationRequestItem, item_id)

    q_mancante = request.form.get('quantity_missing', '')
    arrivo     = request.form.get('expected_arrival', '')
    note_mag   = request.form.get('warehouse_notes', '').strip()

    if q_mancante.isdigit():
        item.quantity_missing = int(q_mancante)
    if arrivo:
        try:
            item.expected_arrival = datetime.strptime(arrivo, '%Y-%m-%d')
        except ValueError:
            pass
    item.warehouse_notes = note_mag or item.warehouse_notes

    db.session.commit()
    flash('Item aggiornato.', 'success')
    return redirect(url_for('magazzino.rda_dettaglio', rda_id=rda_id))


# ------------------------------------------------------------------
# Articoli mancanti (vista aggregata)
# ------------------------------------------------------------------

@magazzino_bp.route('/articoli-mancanti')
@session_check('magazzino')
def articoli_mancanti():
    """
    Mostra tutti gli item con quantity_missing > 0,
    raggruppati per codice articolo.
    """
    items = (ReintegrationRequestItem.query
             .filter(ReintegrationRequestItem.quantity_missing > 0)
             .order_by(ReintegrationRequestItem.expected_arrival.asc().nullslast())
             .all())
    return render_template('magazzino/articoli_mancanti.html',
                           title='Articoli Mancanti', items=items)
