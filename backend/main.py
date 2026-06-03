# main.py
from flask import Flask, render_template, request, session, redirect, url_for, abort
from sqlalchemy import func
from flask_wtf.csrf import CSRFProtect

from core.config import Config
from core.db import db, init_db
from core.cli import register_commands

csrf = CSRFProtect()

# Blueprint
from auth.routes import auth
from admin import admin_bp
from tecnico import tecnico_bp
from magazzino import magazzino_bp
from shared import shared_bp

# Importa tutti i modelli così Flask-Migrate li rileva
from models.user import User
from models.van import Van
from models.panthera_order import PantheraOrder
from models.service_document import ServiceDocument, ServiceDocumentMaterial
from models.reintegration_request import ReintegrationRequest, ReintegrationRequestItem
from models.receipt import Receipt
from models.panthera_sync_log import PantheraSyncLog


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    init_db(app)
    csrf.init_app(app)
    register_commands(app)

    # Context processor: inietta username/role/avatar in TUTTI i template
    # così i blueprint non devono passarli esplicitamente (pattern dai tuoi routes originali)
    @app.context_processor
    def inject_session_vars():
        if 'username' in session:
            return {
                'username': session['username'],
                'role':     session['role'],
                'avatar':   session['username'][0].upper(),
            }
        return {}

    app.register_blueprint(auth)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tecnico_bp)
    app.register_blueprint(magazzino_bp)
    app.register_blueprint(shared_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    @app.route('/furgoni/<van_code>/materiali')
    def furgoni_materiali(van_code):
        van = Van.query.filter_by(code=van_code).first()
        if not van:
            abort(404)

        # Aggregazione materiali da tutti i documenti chiusi del furgone
        doc_ids = [
            d.id for d in
            ServiceDocument.query.filter_by(van_id=van.id, status='closed').all()
        ]

        materiali = []
        last_update = None

        if doc_ids:
            materiali = (
                db.session.query(
                    ServiceDocumentMaterial.part_code,
                    ServiceDocumentMaterial.description,
                    func.sum(ServiceDocumentMaterial.quantity_used).label('qty_totale')
                )
                .filter(ServiceDocumentMaterial.service_document_id.in_(doc_ids))
                .group_by(
                    ServiceDocumentMaterial.part_code,
                    ServiceDocumentMaterial.description
                )
                .order_by(ServiceDocumentMaterial.part_code)
                .all()
            )
            last_doc = (
                ServiceDocument.query
                .filter_by(van_id=van.id, status='closed')
                .order_by(ServiceDocument.closed_at.desc())
                .first()
            )
            last_update = last_doc.closed_at if last_doc else None

        return render_template(
            'furgoni/materiali.html',
            title=f'Materiali – {van.code}',
            van=van,
            materiali=materiali,
            last_update=last_update,
        )

    @app.errorhandler(404)
    @app.errorhandler(500)
    @app.errorhandler(401)
    @app.errorhandler(403)
    def handle_error(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': str(error)}, error.code
        return render_template('error/error.html', error=error), error.code

    return app


app = create_app()

# Dalla documentazione Flask: solo per sviluppo, NON usare in produzione
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9234)
