# main.py
from flask import Flask, render_template, request, session
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

    @app.route('/')
    def index():
        return render_template('landing/index.html', title='PartFlow')

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
