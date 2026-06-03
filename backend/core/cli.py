import os
import click
from flask import Flask

from core.db import db
from models.user import User


def register_commands(app: Flask) -> None:
    @app.cli.command('seed-users')
    def seed_users():
        """Crea gli utenti iniziali (admin, tecnico, magazzino)."""
        utenti = [
            {'username': 'admin', 'password': os.environ.get('SEED_ADMIN_PWD',     'admin123'),     'role': 'admin'},
            {'username': 'marco', 'password': os.environ.get('SEED_TECNICO_PWD',   'tecnico123'),   'role': 'tecnico'},
            {'username': 'sara',  'password': os.environ.get('SEED_MAGAZZINO_PWD', 'magazzino123'), 'role': 'magazzino'},
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
