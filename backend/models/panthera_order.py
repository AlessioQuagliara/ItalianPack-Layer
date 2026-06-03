# models/panthera_order.py
from core.db import db


class PantheraOrder(db.Model):
    __tablename__ = 'panthera_orders'

    id               = db.Column(db.Integer, primary_key=True)
    panthera_id      = db.Column(db.String(64), unique=True, nullable=False)
    panthera_code    = db.Column(db.String(64), nullable=True)
    customer_name    = db.Column(db.String(256), nullable=True)
    customer_code    = db.Column(db.String(64), nullable=True)
    order_type       = db.Column(db.String(64), nullable=True)          # service / material / transfer
    status           = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'cancelled', name='order_status'),
        default='pending', nullable=False
    )
    scheduled_date   = db.Column(db.DateTime, nullable=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    van_id           = db.Column(db.Integer, db.ForeignKey('vans.id'), nullable=True)
    raw_json         = db.Column(db.JSON, nullable=True)                # raw payload from Panthera
    synced_at        = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, server_default=db.func.now())
    updated_at       = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # relationships
    service_documents = db.relationship('ServiceDocument', backref='order', lazy='select')

    def __repr__(self):
        return f'<PantheraOrder {self.panthera_id} [{self.status}]>'
