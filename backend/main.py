# main.py
import click
from flask import Flask, render_template, session

from core.config import Config
from core.db import db, init_db

# Blueprint
from auth.routes import auth
from admin.routes import admin_bp
from tecnico.routes import tecnico_bp
from magazzino.routes import magazzino_bp

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
        return render_template('error/error.html', error=error), error.code

    # ------------------------------------------------------------------
    # Comandi CLI
    # ------------------------------------------------------------------

    @app.cli.command('seed-users')
    def seed_users():
        """Crea gli utenti iniziali (admin, tecnico, magazzino)."""
        utenti = [
            {'username': 'admin',     'password': 'admin123',     'role': 'admin'},
            {'username': 'marco',     'password': 'tecnico123',   'role': 'tecnico'},
            {'username': 'sara',      'password': 'magazzino123', 'role': 'magazzino'},
        ]
        creati = 0
        for dati in utenti:
            if not User.query.filter_by(username=dati['username']).first():
                u = User(username=dati['username'], role=dati['role'])
                u.set_password(dati['password'])
                db.session.add(u)
                creati += 1
                click.echo(f"  Creato: {dati['username']} ({dati['role']})")
            else:
                click.echo(f"  Già esistente: {dati['username']}")
        db.session.commit()
        click.echo(f'Fatto. {creati} utenti creati.')

    return app


app = create_app()

# Dalla documentazione Flask: solo per sviluppo, NON usare in produzione
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8129)
