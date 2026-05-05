# warehouse/routes.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint, abort

warehouse = Blueprint('warehouse', __name__, url_prefix='/warehouse')

must_role = "warehouse"

@warehouse.route("/")
def index_warehouse():
    title = "index"
    return render_template("warehouse/public.html", title=title)


@warehouse.route("/admin/dashboard")
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
    return render_template("spare_parts/dashboard.html", title=title, content=content, role=role)