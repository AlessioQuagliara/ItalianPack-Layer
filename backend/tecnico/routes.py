# tecnico/routes.py
# Blueprint per il ruolo "tecnico"
import os
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import (render_template, redirect, url_for, request,
                   flash, Blueprint, session, current_app)

from core.auth import session_check
from core.db import db
from models.panthera_order import PantheraOrder
from models.service_document import ServiceDocument, ServiceDocumentMaterial
from models.reintegration_request import ReintegrationRequest, ReintegrationRequestItem
from models.receipt import Receipt

tecnico_bp = Blueprint('tecnico', __name__, url_prefix='/tecnico')

ESTENSIONI_CONSENTITE = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def _estensione_valida(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ESTENSIONI_CONSENTITE


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@tecnico_bp.route('/dashboard')
@session_check('tecnico')
def dashboard():
    uid = session['user_id']
    conteggi = {
        'ordini_assegnati':   PantheraOrder.query.filter_by(assigned_user_id=uid, status='pending').count(),
        'documenti_aperti':   ServiceDocument.query.filter_by(tecnico_user_id=uid, status='open').count(),
        'scontrini_pendenti': Receipt.query.filter_by(uploaded_by_user_id=uid, status='pending_ocr').count(),
    }
    ultimi_ordini = (PantheraOrder.query
                     .filter_by(assigned_user_id=uid)
                     .order_by(PantheraOrder.scheduled_date.asc())
                     .limit(5).all())
    return render_template('tecnico/dashboard.html', title='Dashboard', conteggi=conteggi,
                           ultimi_ordini=ultimi_ordini)


# ------------------------------------------------------------------
# Ordini assegnati
# ------------------------------------------------------------------

@tecnico_bp.route('/ordini')
@session_check('tecnico')
def ordini():
    uid   = session['user_id']
    lista = (PantheraOrder.query
             .filter_by(assigned_user_id=uid)
             .order_by(PantheraOrder.scheduled_date.asc())
             .all())
    return render_template('tecnico/ordini.html', title='I Miei Ordini', ordini=lista)


# ------------------------------------------------------------------
# Documenti di servizio (CRUD)
# ------------------------------------------------------------------

@tecnico_bp.route('/documenti')
@session_check('tecnico')
def documenti():
    uid   = session['user_id']
    lista = (ServiceDocument.query
             .filter_by(tecnico_user_id=uid)
             .order_by(ServiceDocument.created_at.desc())
             .all())
    return render_template('tecnico/documenti.html', title='Documenti Servizio', documenti=lista)


@tecnico_bp.route('/documenti/nuovo', methods=['POST'])
@session_check('tecnico')
def documento_nuovo():
    uid = session['user_id']
    doc = ServiceDocument(
        tecnico_user_id    = uid,
        panthera_order_id  = request.form.get('panthera_order_id') or None,
        van_id             = request.form.get('van_id') or None,
        description        = request.form.get('description', '').strip(),
        status             = 'open',
    )
    db.session.add(doc)
    db.session.commit()
    flash('Documento creato.', 'success')
    return redirect(url_for('tecnico.documenti'))


@tecnico_bp.route('/documenti/<int:doc_id>')
@session_check('tecnico')
def documento_dettaglio(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    materiali = doc.materials.all()
    ordini    = PantheraOrder.query.filter_by(assigned_user_id=uid).all()
    return render_template('tecnico/documento_dettaglio.html', title='Documento',
                           doc=doc, materiali=materiali, ordini=ordini)


@tecnico_bp.route('/documenti/<int:doc_id>/materiale', methods=['POST'])
@session_check('tecnico')
def materiale_aggiungi(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()

    if doc.status != 'open':
        flash('Documento non modificabile.', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))

    mat = ServiceDocumentMaterial(
        service_document_id = doc_id,
        part_code           = request.form.get('part_code', '').strip().upper(),
        description         = request.form.get('description', '').strip(),
        quantity_used       = int(request.form.get('quantity_used', 1)),
    )
    db.session.add(mat)
    db.session.commit()
    flash('Materiale aggiunto.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/<int:doc_id>/materiale/<int:mat_id>/elimina', methods=['POST'])
@session_check('tecnico')
def materiale_elimina(doc_id, mat_id):
    uid = session['user_id']
    ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    mat = ServiceDocumentMaterial.query.get_or_404(mat_id)
    db.session.delete(mat)
    db.session.commit()
    flash('Materiale rimosso.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


@tecnico_bp.route('/documenti/<int:doc_id>/chiudi', methods=['POST'])
@session_check('tecnico')
def documento_chiudi(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()
    doc.status    = 'closed'
    doc.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Documento chiuso.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


# ------------------------------------------------------------------
# Richiesta di reintegro (RDA) da documento chiuso
# ------------------------------------------------------------------

@tecnico_bp.route('/documenti/<int:doc_id>/richiedi-rda', methods=['POST'])
@session_check('tecnico')
def richiedi_rda(doc_id):
    uid = session['user_id']
    doc = ServiceDocument.query.filter_by(id=doc_id, tecnico_user_id=uid).first_or_404()

    if doc.status == 'open':
        flash('Chiudi il documento prima di richiedere il reintegro.', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))

    if doc.status == 'rda_requested':
        flash('RDA già inviata per questo documento.', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))

    materiali = doc.materials.all()
    if not materiali:
        flash('Nessun materiale nel documento, impossibile creare RDA.', 'error')
        return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))

    # Crea la RDA
    rda = ReintegrationRequest(
        service_document_id  = doc_id,
        van_id               = doc.van_id,
        requested_by_user_id = uid,
        status               = 'pending',
        is_urgent            = bool(request.form.get('urgente')),
        notes                = request.form.get('note', '').strip(),
    )
    db.session.add(rda)
    db.session.flush()  # ottieni l'ID prima del commit

    # Crea gli item dalla lista materiali
    for mat in materiali:
        item = ReintegrationRequestItem(
            reintegration_request_id = rda.id,
            part_code                = mat.part_code,
            description              = mat.description,
            quantity_requested       = mat.quantity_used,
        )
        db.session.add(item)

    doc.status = 'rda_requested'
    db.session.commit()
    flash('RDA inviata al magazzino.', 'success')
    return redirect(url_for('tecnico.documento_dettaglio', doc_id=doc_id))


# ------------------------------------------------------------------
# Scontrini: upload + OCR
# ------------------------------------------------------------------

@tecnico_bp.route('/scontrini')
@session_check('tecnico')
def scontrini():
    uid   = session['user_id']
    lista = (Receipt.query
             .filter_by(uploaded_by_user_id=uid)
             .order_by(Receipt.created_at.desc())
             .all())
    ordini = PantheraOrder.query.filter_by(assigned_user_id=uid).all()
    return render_template('tecnico/scontrini.html', title='Scontrini', scontrini=lista,
                           ordini=ordini)


@tecnico_bp.route('/scontrini/upload', methods=['POST'])
@session_check('tecnico')
def scontrino_upload():
    uid  = session['user_id']
    file = request.files.get('file')

    if not file or file.filename == '':
        flash('Nessun file selezionato.', 'error')
        return redirect(url_for('tecnico.scontrini'))

    if not _estensione_valida(file.filename):
        flash('Formato non supportato. Usa PNG, JPG o PDF.', 'error')
        return redirect(url_for('tecnico.scontrini'))

    cartella = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(cartella, exist_ok=True)
    nome_file = secure_filename(file.filename)
    percorso  = os.path.join(cartella, nome_file)
    file.save(percorso)

    scontrino = Receipt(
        uploaded_by_user_id = uid,
        panthera_order_id   = request.form.get('panthera_order_id') or None,
        filename            = nome_file,
        status              = 'pending_ocr',
    )
    db.session.add(scontrino)
    db.session.commit()

    # Avvia OCR in background
    from services.ocr_service import OcrService
    OcrService().avvia_ocr_asincrono(scontrino.id, percorso, current_app._get_current_object())

    flash('Scontrino caricato. OCR in elaborazione.', 'success')
    return redirect(url_for('tecnico.scontrini'))
