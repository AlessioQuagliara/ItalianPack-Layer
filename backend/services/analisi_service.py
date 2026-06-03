# services/analisi_service.py
from datetime import date as date_type, datetime, timedelta
from sqlalchemy import func, distinct, text

from core.db import db
from models.service_document import ServiceDocument, ServiceDocumentMaterial
from models.van import Van


# ---------------------------------------------------------------------------
# Filter parsing (shared between magazzino and admin blueprints)
# ---------------------------------------------------------------------------

def parse_analisi_filters(args):
    """
    Parse ImmutableMultiDict (request.args or request.form) into:
      filters    — dict for service queries
      filtri_raw — dict of raw string values for form repopulation
      days_range — int, number of days in the selected period
    """
    periodo   = args.get('periodo', '30gg')
    van_id    = args.get('van_id', type=int) or None
    commessa  = args.get('commessa', '').strip()
    stato_doc = args.get('stato_documento', 'closed')
    top_n_raw = args.get('top_n', '20')
    top_n     = None if top_n_raw == 'all' else int(top_n_raw)

    today = date_type.today()

    if periodo == '7gg':
        date_from, date_to = today - timedelta(days=7), today
    elif periodo == '90gg':
        date_from, date_to = today - timedelta(days=90), today
    elif periodo == 'anno':
        date_from, date_to = date_type(today.year, 1, 1), today
    elif periodo == 'custom':
        df = args.get('date_from', '')
        dt = args.get('date_to', '')
        try:
            date_from = datetime.strptime(df, '%Y-%m-%d').date() if df else today - timedelta(days=30)
        except ValueError:
            date_from = today - timedelta(days=30)
        try:
            date_to = datetime.strptime(dt, '%Y-%m-%d').date() if dt else today
        except ValueError:
            date_to = today
    else:  # default 30gg
        periodo = '30gg'
        date_from, date_to = today - timedelta(days=30), today

    days_range = max((date_to - date_from).days, 1)

    filters = {
        'date_from':       date_from,
        'date_to':         date_to,
        'van_id':          van_id,
        'commessa':        commessa,
        'stato_documento': stato_doc,
        'top_n':           top_n,
    }
    filtri_raw = {
        'periodo':         periodo,
        'van_id':          str(van_id) if van_id else '',
        'commessa':        commessa,
        'stato_documento': stato_doc,
        'top_n':           top_n_raw,
        'date_from':       args.get('date_from', ''),
        'date_to':         args.get('date_to', ''),
    }
    return filters, filtri_raw, days_range


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _apply_doc_filters(q, filters: dict):
    """Apply WHERE clauses on ServiceDocument (already joined in query q)."""
    stato = filters.get('stato_documento', 'closed')
    if stato == 'closed':
        q = q.filter(ServiceDocument.status == 'closed')

    date_from = filters.get('date_from')
    date_to   = filters.get('date_to')
    if date_from:
        q = q.filter(
            ServiceDocument.created_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        q = q.filter(
            ServiceDocument.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time())
        )

    van_id = filters.get('van_id')
    if van_id:
        q = q.filter(ServiceDocument.van_id == van_id)

    commessa = filters.get('commessa', '').strip()
    if commessa:
        q = q.filter(ServiceDocument.commessa.ilike(f'%{commessa}%'))

    return q


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AnalisiService:

    @staticmethod
    def pezzi_piu_richiesti(filters: dict) -> list[dict]:
        top_n = filters.get('top_n')

        q = (
            db.session.query(
                ServiceDocumentMaterial.part_code,
                ServiceDocumentMaterial.description,
                func.sum(ServiceDocumentMaterial.quantity_used).label('tot_quantita'),
                func.count(distinct(ServiceDocument.id)).label('n_documenti'),
                func.count(distinct(ServiceDocument.van_id)).label('n_furgoni'),
                func.count(distinct(ServiceDocument.commessa)).label('n_commesse'),
                func.max(ServiceDocument.created_at).label('ultimo_utilizzo'),
            )
            .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
        )
        q = _apply_doc_filters(q, filters)
        q = (
            q
            .group_by(ServiceDocumentMaterial.part_code, ServiceDocumentMaterial.description)
            .order_by(func.sum(ServiceDocumentMaterial.quantity_used).desc())
        )
        if top_n is not None:
            q = q.limit(top_n)

        return [
            {
                'part_code':       r.part_code,
                'description':     r.description or '—',
                'tot_quantita':    int(r.tot_quantita),
                'n_documenti':     int(r.n_documenti),
                'n_furgoni':       int(r.n_furgoni),
                'n_commesse':      int(r.n_commesse),
                'ultimo_utilizzo': r.ultimo_utilizzo,
            }
            for r in q.all()
        ]

    @staticmethod
    def breakdown_per_furgone(filters: dict, part_codes: list) -> dict:
        """Returns {part_code: [{'van_code': ..., 'qty': ...}, ...]}."""
        if not part_codes:
            return {}

        q = (
            db.session.query(
                ServiceDocumentMaterial.part_code,
                Van.code.label('van_code'),
                func.sum(ServiceDocumentMaterial.quantity_used).label('qty'),
            )
            .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
            .outerjoin(Van, Van.id == ServiceDocument.van_id)
            .filter(ServiceDocumentMaterial.part_code.in_(part_codes))
        )
        q = _apply_doc_filters(q, filters)
        q = (
            q
            .group_by(ServiceDocumentMaterial.part_code, Van.code)
            .order_by(ServiceDocumentMaterial.part_code,
                      func.sum(ServiceDocumentMaterial.quantity_used).desc())
        )

        result: dict = {}
        for r in q.all():
            result.setdefault(r.part_code, []).append(
                {'van_code': r.van_code or '—', 'qty': int(r.qty)}
            )
        return result

    @staticmethod
    def breakdown_per_commessa(filters: dict, part_codes: list) -> dict:
        """Returns {part_code: [{'commessa': ..., 'qty': ...}, ...]}."""
        if not part_codes:
            return {}

        q = (
            db.session.query(
                ServiceDocumentMaterial.part_code,
                ServiceDocument.commessa,
                func.sum(ServiceDocumentMaterial.quantity_used).label('qty'),
            )
            .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
            .filter(
                ServiceDocumentMaterial.part_code.in_(part_codes),
                ServiceDocument.commessa.isnot(None),
            )
        )
        q = _apply_doc_filters(q, filters)
        q = (
            q
            .group_by(ServiceDocumentMaterial.part_code, ServiceDocument.commessa)
            .order_by(ServiceDocumentMaterial.part_code,
                      func.sum(ServiceDocumentMaterial.quantity_used).desc())
        )

        result: dict = {}
        for r in q.all():
            result.setdefault(r.part_code, []).append(
                {'commessa': r.commessa, 'qty': int(r.qty)}
            )
        return result

    @staticmethod
    def top_furgoni(filters: dict) -> list[dict]:
        q = (
            db.session.query(
                Van.code.label('van_code'),
                func.sum(ServiceDocumentMaterial.quantity_used).label('qty_tot'),
                func.count(distinct(ServiceDocumentMaterial.part_code)).label('pezzi_distinti'),
                func.count(distinct(ServiceDocument.id)).label('n_documenti'),
            )
            .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
            .join(Van, Van.id == ServiceDocument.van_id)
        )
        q = _apply_doc_filters(q, filters)
        q = (
            q
            .group_by(Van.code)
            .order_by(func.sum(ServiceDocumentMaterial.quantity_used).desc())
            .limit(5)
        )
        return [
            {
                'van_code':       r.van_code,
                'qty_tot':        int(r.qty_tot),
                'pezzi_distinti': int(r.pezzi_distinti),
                'n_documenti':    int(r.n_documenti),
            }
            for r in q.all()
        ]

    @staticmethod
    def andamento_nel_tempo(filters: dict, group_by: str = 'week') -> list[dict]:
        trunc = 'week' if group_by == 'week' else 'month'

        q = (
            db.session.query(
                func.date_trunc(trunc, ServiceDocument.created_at).label('periodo'),
                func.sum(ServiceDocumentMaterial.quantity_used).label('qty'),
            )
            .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
        )
        q = _apply_doc_filters(q, filters)
        q = q.group_by(text('periodo')).order_by(text('periodo'))

        rows = q.all()
        if not rows:
            return []

        max_qty = max(int(r.qty) for r in rows) or 1
        result = []
        for r in rows:
            qty = int(r.qty)
            if r.periodo:
                label = (r.periodo.strftime('Sett. %W – %Y')
                         if trunc == 'week'
                         else r.periodo.strftime('%B %Y').capitalize())
            else:
                label = '—'
            result.append({'label': label, 'qty': qty, 'pct': int(qty / max_qty * 100)})
        return result

    @staticmethod
    def kpi(filters: dict, risultati: list[dict]) -> dict:
        pezzi_distinti = len(risultati)
        qty_totale     = sum(r['tot_quantita'] for r in risultati)

        # Documento con più materiali nel periodo
        q_doc = (
            db.session.query(
                ServiceDocument.id,
                ServiceDocument.description,
                func.count(ServiceDocumentMaterial.id).label('n_mat'),
            )
            .join(ServiceDocumentMaterial,
                  ServiceDocumentMaterial.service_document_id == ServiceDocument.id)
        )
        q_doc = _apply_doc_filters(q_doc, filters)
        q_doc = (q_doc
                 .group_by(ServiceDocument.id, ServiceDocument.description)
                 .order_by(func.count(ServiceDocumentMaterial.id).desc())
                 .limit(1))
        doc_top = q_doc.first()

        # Furgone più attivo (solo se van non filtrato)
        furgone_top = None
        if not filters.get('van_id'):
            q_van = (
                db.session.query(
                    Van.code.label('van_code'),
                    func.sum(ServiceDocumentMaterial.quantity_used).label('qty'),
                )
                .join(ServiceDocument, ServiceDocument.id == ServiceDocumentMaterial.service_document_id)
                .join(Van, Van.id == ServiceDocument.van_id)
            )
            q_van = _apply_doc_filters(q_van, filters)
            q_van = (q_van
                     .group_by(Van.code)
                     .order_by(func.sum(ServiceDocumentMaterial.quantity_used).desc())
                     .limit(1))
            top = q_van.first()
            if top:
                furgone_top = {'van_code': top.van_code, 'qty': int(top.qty)}

        return {
            'pezzi_distinti': pezzi_distinti,
            'qty_totale':     qty_totale,
            'doc_top': (
                {
                    'label': doc_top.description or f'Doc #{doc_top.id}',
                    'n_mat': int(doc_top.n_mat),
                }
                if doc_top else None
            ),
            'furgone_top': furgone_top,
        }
