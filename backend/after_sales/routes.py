# after_sales/routes.py
from flask import render_template, url_for, redirect, session, Blueprint, abort, request
from functools import wraps
from models.missing_part import table_datas, columns

after_sales = Blueprint('after_sales', __name__, url_prefix='/after_sales')

must_role = "after_sales"

@after_sales.route("/")
def index_after_sales():
    title = "index"
    return render_template("after_sales/public.html", title=title)

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
    

@after_sales.route("/admin/dashboard")
@session_check(must_role)
def dashboard():
    title = "Dashboard"
    role = session['role']
    username = session['username']
    avatar = username[0]
    return render_template(
        "after_sales/dashboard.html", 
        title=title, 
        role=role, 
        username=username, 
        avatar=avatar
        )


@after_sales.route("/admin/missed_parts")
@session_check(must_role)
def missed_parts():
    title = "Missed-Parts"
    role = session['role']
    username = session['username']
    avatar = username[0]

    return render_template(
        "after_sales/missed_part.html", 
        title=title,
        must_role=must_role,
        role=role, 
        username=username,
        avatar=avatar,
        columns=columns,
        table_datas=table_datas,
        partial_path="after_sales/partials/missed_list.html",
        partial_form_add="after_sales/partials/missed_add_form.html",
        partial_form_delete="after_sales/partials/missed_delete_form.html",
        )

@after_sales.route("/admin/manage_missed_part", methods=['POST'])
@session_check(must_role)
def manage_missed_part():
    if request.method == 'POST':
        code = request.form.get("code")
        quantity = request.form.get("quantity")
        print(code, quantity)
    return redirect(url_for('after_sales.missed_parts'))

@after_sales.route("/admin/settings")
@session_check(must_role)
def settings():
    title = "Settings"
    role = session['role']
    username = session['username']
    avatar = username[0]
    return render_template(
        "after_sales/settings.html", 
        title=title, 
        role=role, 
        username=username,
        avatar=avatar
        )
    

