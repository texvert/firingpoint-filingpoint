import functools

from flask import g, redirect, request, session, url_for

from .db import get_db
from .timestamps import from_text, utc_now

SESSION_KEY = "account"


def log_in(kind, account_id):
    session.clear()
    session[SESSION_KEY] = {"kind": kind, "id": account_id}
    session.permanent = True


def log_out():
    session.clear()


def temporary_password_expired(account):
    if not account["must_change_password"] or account["temp_password_expires_at"] is None:
        return False
    return from_text(account["temp_password_expires_at"]) < utc_now()


def load_current_account():
    g.admin = None
    account = session.get(SESSION_KEY)
    if account is None or account.get("kind") != "admin":
        return
    admin = get_db().execute(
        "SELECT * FROM admins WHERE id = ? AND disabled_at IS NULL", (account["id"],)
    ).fetchone()
    if admin is None or temporary_password_expired(admin):
        session.clear()
        return
    g.admin = admin


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.admin is None:
            return redirect(url_for("admin.login"))
        if g.admin["must_change_password"] and request.endpoint != "admin.change_password":
            return redirect(url_for("admin.change_password"))
        return view(**kwargs)

    return wrapped_view


def init_app(app):
    app.before_request(load_current_account)
