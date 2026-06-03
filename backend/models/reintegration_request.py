# models/reintegration_request.py
from core.db import db


class ReintegrationRequest(db.Model):
    __tablename__ = 'reintegration_requests'

    id                  = db.Column(db.Integer, primary_key=True)
    service_document_id = db.Column(db.Integer, db.ForeignKey('service_documents.id'), nullable=False)
    van_id              = db.Column(db.Integer, db.ForeignKey('vans.id'), nullable=True)  # snapshot del furgone al momento della RDA, non derivato dal documento
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status              = db.Column(
        db.Enum('pending', 'in_preparation', 'ready', 'delivered', name='rda_status'),
        default='pending', nullable=False
    )
    is_urgent           = db.Column(db.Boolean, default=False, nullable=False)
    notes               = db.Column(db.Text, nullable=True)
    created_at          = db.Column(db.DateTime, server_default=db.func.now())
    updated_at          = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # relationships
    items           = db.relationship('ReintegrationRequestItem', backref='rda', lazy='select', cascade='all, delete-orphan')
    requested_by    = db.relationship('User', foreign_keys=[requested_by_user_id])
    van             = db.relationship('Van', foreign_keys=[van_id])

    def __repr__(self):
        return f'<RDA {self.id} [{self.status}]>'


class ReintegrationRequestItem(db.Model):
    __tablename__ = 'reintegration_request_items'

    id                        = db.Column(db.Integer, primary_key=True)
    reintegration_request_id  = db.Column(db.Integer, db.ForeignKey('reintegration_requests.id'), nullable=False)
    part_code                 = db.Column(db.String(64), nullable=False)
    description               = db.Column(db.String(256), nullable=True)
    quantity_requested        = db.Column(db.Integer, default=1, nullable=False)
    quantity_missing          = db.Column(db.Integer, default=0, nullable=False)  # warehouse fills this
    expected_arrival          = db.Column(db.DateTime, nullable=True)             # warehouse fills this
    warehouse_notes           = db.Column(db.Text, nullable=True)
    created_at                = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<RDAItem {self.part_code} x{self.quantity_requested}>'
