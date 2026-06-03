# models/van.py
from core.db import db


class Van(db.Model):
    __tablename__ = 'vans'

    id           = db.Column(db.Integer, primary_key=True)
    code         = db.Column(db.String(32), unique=True, nullable=False)
    name         = db.Column(db.String(128), nullable=False)
    plate_number = db.Column(db.String(16), nullable=True)
    is_active    = db.Column(db.Boolean, default=True, nullable=False)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())

    # relationships
    orders            = db.relationship('PantheraOrder', backref='van', lazy='select')
    service_documents = db.relationship('ServiceDocument', backref='van', lazy='select')

    def __repr__(self):
        return f'<Van {self.code} - {self.plate_number}>'
