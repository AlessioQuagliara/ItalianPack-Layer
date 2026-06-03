import os

from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, request, flash, session, current_app

from core.auth import session_check
from core.db import db
from models.panthera_order import PantheraOrder
from models.receipt import Receipt
from services.ocr_service import OcrService
from tecnico import tecnico_bp

ESTENSIONI_CONSENTITE = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def _estensione_valida(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ESTENSIONI_CONSENTITE


@tecnico_bp.route('/scontrini')
@session_check('tecnico')
def scontrini():
    uid    = session['user_id']
    lista  = (Receipt.query
              .filter_by(uploaded_by_user_id=uid)
              .order_by(Receipt.created_at.desc())
              .all())
    ordini = PantheraOrder.query.filter_by(assigned_user_id=uid).all()
    return render_template('tecnico/scontrini.html', title='Scontrini',
                           scontrini=lista, ordini=ordini)


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

    cartella  = current_app.config.get('UPLOAD_FOLDER', 'uploads')
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

    OcrService().avvia_ocr_asincrono(scontrino.id, percorso, current_app._get_current_object())

    flash('Scontrino caricato. OCR in elaborazione.', 'success')
    return redirect(url_for('tecnico.scontrini'))
