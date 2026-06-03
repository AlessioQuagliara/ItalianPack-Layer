# admin/analisi.py
from datetime import date as date_type
from flask import render_template, request, url_for

from core.auth import session_check
from admin import admin_bp
from magazzino.routes import _analisi_context, _make_csv_response
from services.analisi_service import AnalisiService, parse_analisi_filters


@admin_bp.route('/analisi')
@session_check('admin')
def analisi():
    ctx = _analisi_context(request.args, 'admin')
    return render_template('magazzino/analisi.html', **ctx)


@admin_bp.route('/analisi/export')
@session_check('admin')
def analisi_export():
    filters, _, _ = parse_analisi_filters(request.args)
    filters['top_n'] = None
    risultati = AnalisiService.pezzi_piu_richiesti(filters)
    fname = f'analisi_pezzi_{date_type.today().strftime("%Y%m%d")}.csv'
    return _make_csv_response(risultati, fname)


@admin_bp.route('/analisi/export-selected', methods=['POST'])
@session_check('admin')
def analisi_export_selected():
    selected  = set(request.form.getlist('ids[]'))
    filters, _, _ = parse_analisi_filters(request.form)
    filters['top_n'] = None
    risultati = AnalisiService.pezzi_piu_richiesti(filters)
    if selected:
        risultati = [r for r in risultati if r['part_code'] in selected]
    fname = f'analisi_pezzi_sel_{date_type.today().strftime("%Y%m%d")}.csv'
    return _make_csv_response(risultati, fname)
