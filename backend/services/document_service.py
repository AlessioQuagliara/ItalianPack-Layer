from core.db import db
from models.service_document import ServiceDocument
from models.reintegration_request import ReintegrationRequest, ReintegrationRequestItem


def crea_rda_da_documento(
    doc: ServiceDocument,
    uid: int,
    urgente: bool,
    note: str,
) -> ReintegrationRequest:
    """
    Crea una RDA e i suoi item a partire da un documento di servizio chiuso.

    Raises ValueError per stati non validi del documento.
    Non fa commit: responsabilità del chiamante.
    """
    if doc.status == 'open':
        raise ValueError('Chiudi il documento prima di richiedere il reintegro.')
    if doc.status == 'rda_requested':
        raise ValueError('RDA già inviata per questo documento.')
    if not doc.materials:
        raise ValueError('Nessun materiale nel documento, impossibile creare RDA.')

    rda = ReintegrationRequest(
        service_document_id  = doc.id,
        van_id               = doc.van_id,
        requested_by_user_id = uid,
        status               = 'pending',
        is_urgent            = urgente,
        notes                = note,
    )
    db.session.add(rda)
    db.session.flush()  # necessario per ottenere rda.id prima del commit

    for mat in doc.materials:
        db.session.add(ReintegrationRequestItem(
            reintegration_request_id = rda.id,
            part_code                = mat.part_code,
            description              = mat.description,
            quantity_requested       = mat.quantity_used,
        ))

    doc.status = 'rda_requested'
    return rda
