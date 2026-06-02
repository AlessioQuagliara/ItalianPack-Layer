# models/user.py
from werkzeug.security import generate_password_hash, check_password_hash
from core.db import db


class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.Enum('admin', 'tecnico', 'magazzino', name='user_role'), nullable=False)
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # relationships
    orders            = db.relationship('PantheraOrder', backref='assigned_user', lazy='dynamic', foreign_keys='PantheraOrder.assigned_user_id')
    service_documents = db.relationship('ServiceDocument', backref='tecnico', lazy='dynamic', foreign_keys='ServiceDocument.tecnico_user_id')
    receipts          = db.relationship('Receipt', backref='uploaded_by', lazy='dynamic', foreign_keys='Receipt.uploaded_by_user_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
