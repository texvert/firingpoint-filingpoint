import functools

from flask import g, redirect, session, url_for

from .db import get_db

SESSION_KEY = "account"


def log_in(kind, account_id):
    session.clear()
    session[SESSION_KEY] = {"kind": kind, "id": account_id}
    session.permanent = True


def log_out():
    session.clear()


def load_current_account():
    g.admin = None
    account = session.get(SESSION_KEY)
    if account is None or account.get("kind") != "admin":
        return
    admin = get_db().execute(
        "SELECT * FROM admins WHERE id = ? AND disabled_at IS NULL", (account["id"],)
    ).fetchone()
    if admin is None:
        session.clear()
        return
    g.admin = admin


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.admin is None:
            return redirect(url_for("admin.login"))
        return view(**kwargs)

    return wrapped_view


def init_app(app):
    app.before_request(load_current_account)
