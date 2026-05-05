# spare_parts/routes.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint

spare_parts = Blueprint('spare_parts', __name__, url_prefix='/spare_parts')

@spare_parts.route("/spare_parts")
def index_spare_parts():
    title = "index"
    return render_template("spare_parts/public.html", title=title)

@spare_parts.route("/admin/dashboard")
def spare_parts_dashboard():
    title = "Dashboard"
    content = None
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('login'))
    else:
        content = f"Benvenuto {session['username']}!"
        role = session['role']
    return render_template("admin/dashboard.html", title=title, content=content, role=role)