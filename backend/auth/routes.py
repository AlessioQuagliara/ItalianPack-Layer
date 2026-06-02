# auth/routes.py
from flask import render_template, url_for, request, redirect, session, Blueprint

from models.user import User

auth = Blueprint('auth', __name__, url_prefix='/auth')

# Mappa ruolo → blueprint di destinazione dopo il login
REDIRECT_PER_RUOLO = {
    'admin':     'admin.dashboard',
    'tecnico':   'tecnico.dashboard',
    'magazzino': 'magazzino.dashboard',
}


@auth.route('/login', methods=['GET', 'POST'])
def login():
    title = 'Login'
    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        utente = User.query.filter_by(username=username, is_active=True).first()

        if utente and utente.check_password(password):
            session['username'] = utente.username
            session['role']     = utente.role
            session['user_id']  = utente.id

            destinazione = REDIRECT_PER_RUOLO.get(utente.role)
            if destinazione:
                return redirect(url_for(destinazione))

            return 'Ruolo non riconosciuto.', 401

        error = 'Credenziali non valide o utente disattivato.'

    return render_template('landing/login.html', title=title, error=error)


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
