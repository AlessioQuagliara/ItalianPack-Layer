# core/auth.py
from functools import wraps
from flask import session, redirect, url_for, abort


def session_check(*allowed_roles):
    """
    Decorator that verifies an active session and optionally restricts to specific roles.

    Usage:
        @session_check('responsabile')
        @session_check('tecnico', 'responsabile')
        @session_check()  # any authenticated user
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'username' not in session or 'role' not in session:
                return redirect(url_for('auth.login'))
            if allowed_roles and session['role'] not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
