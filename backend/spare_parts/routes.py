# spare_parts/routes.py
from functools import wraps
from flask import render_template, url_for, redirect, session, Blueprint, abort

spare_parts = Blueprint('spare_parts', __name__, url_prefix='/spare_parts')

must_role = "spare_parts"

@spare_parts.route("/")
def index_spare_parts():
    title = "index"
    return render_template("spare_parts/public.html", title=title)

def session_check(must_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'username' not in session or 'role' not in session:
                return redirect(url_for('auth.login'))
            
            if session['role'] != must_role:
                abort(403)

            return f(*args, **kwargs)
        return wrapper
    return decorator

@spare_parts.route("/admin/dashboard")
def dashboard():
    title = "Dashboard"
    content = None
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('auth.login'))
    else:
        if session['role'] != must_role:
            abort(403)
        
        content = f"Benvenuto {session['username']}!"
        role = session['role']
        username = session['username']
    return render_template("spare_parts/dashboard.html", title=title, content=content, role=role, username=username)