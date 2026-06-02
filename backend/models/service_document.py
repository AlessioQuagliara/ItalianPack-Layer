# models/service_document.py
from core.db import db


class ServiceDocument(db.Model):
    __tablename__ = 'service_documents'

    id               = db.Column(db.Integer, primary_key=True)
    panthera_order_id = db.Column(db.Integer, db.ForeignKey('panthera_orders.id'), nullable=True)
    tecnico_user_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    van_id           = db.Column(db.Integer, db.ForeignKey('vans.id'), nullable=True)
    description      = db.Column(db.Text, nullable=True)
    status           = db.Column(
        db.Enum('open', 'closed', 'rda_requested', name='service_doc_status'),
        default='open', nullable=False
    )
    notes            = db.Column(db.Text, nullable=True)
    closed_at        = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, server_default=db.func.now())
    updated_at       = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # relationships
    materials             = db.relationship('ServiceDocumentMaterial', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    reintegration_requests = db.relationship('ReintegrationRequest', backref='service_document', lazy='dynamic')

    def __repr__(self):
        return f'<ServiceDocument {self.id} [{self.status}]>'


class ServiceDocumentMaterial(db.Model):
    __tablename__ = 'service_document_materials'

    id                  = db.Column(db.Integer, primary_key=True)
    service_document_id = db.Column(db.Integer, db.ForeignKey('service_documents.id'), nullable=False)
    part_code           = db.Column(db.String(64), nullable=False)
    description         = db.Column(db.String(256), nullable=True)
    quantity_used       = db.Column(db.Integer, default=1, nullable=False)
    created_at          = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Material {self.part_code} x{self.quantity_used}>'
