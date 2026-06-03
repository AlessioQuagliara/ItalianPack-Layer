# magazzino/routes.py
import csv
from datetime import datetime, date as date_type
from io import StringIO

from flask import render_template, redirect, url_for, request, flash, make_response

from core.auth import session_check
from core.db import db
from models.reintegration_request import ReintegrationRequest, ReintegrationRequestItem
from models.panthera_order import PantheraOrder
from models.van import Van
from magazzino import magazzino_bp
from services.analisi_service import AnalisiService, parse_analisi_filters


def _parse_date(value: str):
    """Restituisce un oggetto date se il valore è valido, altrimenti None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None

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
    return render_template('magazzino/rda.html', title='Richieste',
                           rda_list=lista, filtro=filtro, stati=STATI_RDA_VALIDI)


@magazzino_bp.route('/rda/<int:rda_id>')
@session_check('magazzino')
def rda_dettaglio(rda_id):
    rda   = db.get_or_404(ReintegrationRequest, rda_id)
    items = rda.items
    return render_template('magazzino/rda_dettaglio.html', title=f'Richiesta #{rda_id}',
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
        flash(f'Richiesta #{rda_id} aggiornata: {nuovo}.', 'success')
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
    flash(f'{len(aggiornate)} richieste aggiornate a "{nuovo}".', 'success')
    return redirect(url_for('magazzino.rda'))


# ------------------------------------------------------------------
# Aggiorna richiesta (stato + campi Panthera + data prevista + note)
# ------------------------------------------------------------------

@magazzino_bp.route('/richieste/<int:rda_id>/aggiorna', methods=['POST'])
@session_check('magazzino')
def richiesta_aggiorna(rda_id):
    rda = db.get_or_404(ReintegrationRequest, rda_id)

    nuovo_stato = request.form.get('status', '')
    if nuovo_stato in STATI_RDA_VALIDI:
        rda.status = nuovo_stato

    rda.rda_panthera_date = _parse_date(request.form.get('rda_panthera_date', ''))
    codice = request.form.get('rda_panthera_code', '').strip()
    rda.rda_panthera_code = codice or None
    rda.expected_arrival  = _parse_date(request.form.get('expected_arrival', ''))
    note = request.form.get('warehouse_notes', '').strip()
    rda.warehouse_notes   = note or None

    db.session.commit()
    flash('Richiesta aggiornata.', 'success')
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
# Analisi pezzi
# ------------------------------------------------------------------

def _analisi_context(args, blueprint: str) -> dict:
    filters, filtri_raw, days_range = parse_analisi_filters(args)
    vans     = Van.query.filter_by(is_active=True).order_by(Van.code).all()
    risultati = AnalisiService.pezzi_piu_richiesti(filters)
    part_codes = [r['part_code'] for r in risultati]

    kpi           = AnalisiService.kpi(filters, risultati)
    van_breakdown = AnalisiService.breakdown_per_furgone(filters, part_codes)
    com_breakdown = AnalisiService.breakdown_per_commessa(filters, part_codes)

    top_furgoni = []
    if not filters.get('van_id'):
        top_furgoni = AnalisiService.top_furgoni(filters)

    andamento = []
    if days_range > 7:
        group_by  = 'month' if days_range > 90 else 'week'
        andamento = AnalisiService.andamento_nel_tempo(filters, group_by)

    return dict(
        title='Analisi Pezzi',
        vans=vans,
        filtri_raw=filtri_raw,
        filters=filters,
        days_range=days_range,
        risultati=risultati,
        kpi=kpi,
        van_breakdown=van_breakdown,
        com_breakdown=com_breakdown,
        top_furgoni=top_furgoni,
        andamento=andamento,
        analisi_url=url_for(f'{blueprint}.analisi'),
        export_url=url_for(f'{blueprint}.analisi_export'),
        export_selected_url=url_for(f'{blueprint}.analisi_export_selected'),
    )


def _make_csv_response(risultati: list, filename: str):
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Codice', 'Descrizione', 'Qty Totale', 'N° Documenti', 'N° Furgoni', 'Ultimo Utilizzo'])
    for r in risultati:
        writer.writerow([
            r['part_code'],
            r['description'],
            r['tot_quantita'],
            r['n_documenti'],
            r['n_furgoni'],
            r['ultimo_utilizzo'].strftime('%d/%m/%Y') if r['ultimo_utilizzo'] else '',
        ])
    resp = make_response(si.getvalue())
    resp.headers['Content-Disposition'] = f'attachment; filename={filename}'
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return resp


@magazzino_bp.route('/analisi')
@session_check('magazzino')
def analisi():
    ctx = _analisi_context(request.args, 'magazzino')
    return render_template('magazzino/analisi.html', **ctx)


@magazzino_bp.route('/analisi/export')
@session_check('magazzino')
def analisi_export():
    filters, _, _ = parse_analisi_filters(request.args)
    filters['top_n'] = None  # nessun limite sull'export
    risultati = AnalisiService.pezzi_piu_richiesti(filters)
    fname = f'analisi_pezzi_{date_type.today().strftime("%Y%m%d")}.csv'
    return _make_csv_response(risultati, fname)


@magazzino_bp.route('/analisi/export-selected', methods=['POST'])
@session_check('magazzino')
def analisi_export_selected():
    selected = set(request.form.getlist('ids[]'))
    filters, _, _ = parse_analisi_filters(request.form)
    filters['top_n'] = None
    risultati = AnalisiService.pezzi_piu_richiesti(filters)
    if selected:
        risultati = [r for r in risultati if r['part_code'] in selected]
    fname = f'analisi_pezzi_sel_{date_type.today().strftime("%Y%m%d")}.csv'
    return _make_csv_response(risultati, fname)


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
