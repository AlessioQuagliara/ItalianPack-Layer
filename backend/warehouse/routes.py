# warehouse/routes.py
from flask import Flask, flash, render_template, url_for, request, redirect, session, Blueprint

warehouse = Blueprint('warehouse', __name__, url_prefix='/warehouse')

@warehouse.route("/warehouse")
def index_warehouse():
    title = "index"
    return render_template("warehouse/public.html", title=title)


@warehouse.route("/admin/dashboard")
def warehouse_dashboard():
    title = "Dashboard"
    content = None
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('login'))
    else:
        content = f"Benvenuto {session['username']}!"
        role = session['role']
    return render_template("admin/dashboard.html", title=title, content=content, role=role)