# auth/routes.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint
from models.user import Utente, utenti

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route("/login", methods=['GET', 'POST'])
def login():
    title = "Login"
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        for utente in utenti:
            if username == utente.username and password == utente.password:
                if not utente.username or not utente.role:
                    pass
                else:
                    session['username'] = username
                    session['role'] = utente.role
                    if utente.role == 'spare_parts':
                        return redirect(url_for('spare_parts.dashboard'))
                    elif utente.role == 'warehouse':
                        return redirect(url_for('warehouse.dashboard'))
                    else:
                        return "Not authorized", 401

                
        error = "invalid credentials"
    
    return render_template("landing/login.html", title=title, error=error)



@auth.route("/logout")
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('auth.login'))