from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("user_id"):
            flash("Debés iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acceso restringido a administradores", "danger")
            return redirect("/")
        return f(*args, **kwargs)
    return wrap
