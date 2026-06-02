# models/receipt.py
from core.db import db


class Receipt(db.Model):
    __tablename__ = 'receipts'

    id                  = db.Column(db.Integer, primary_key=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    panthera_order_id   = db.Column(db.Integer, db.ForeignKey('panthera_orders.id'), nullable=True)
    filename            = db.Column(db.String(256), nullable=False)
    status              = db.Column(
        db.Enum('pending_ocr', 'ocr_done', 'validated', 'rejected', name='receipt_status'),
        default='pending_ocr', nullable=False
    )
    ocr_raw_text        = db.Column(db.Text, nullable=True)
    ocr_date            = db.Column(db.Date, nullable=True)
    ocr_supplier        = db.Column(db.String(256), nullable=True)
    ocr_total           = db.Column(db.Numeric(10, 2), nullable=True)
    notes               = db.Column(db.Text, nullable=True)
    created_at          = db.Column(db.DateTime, server_default=db.func.now())
    updated_at          = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    order = db.relationship('PantheraOrder', foreign_keys=[panthera_order_id])

    def __repr__(self):
        return f'<Receipt {self.id} [{self.status}]>'
