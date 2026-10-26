from flask import Blueprint, g, redirect, render_template, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import admin_required, log_in, log_out
from .db import get_db
from .forms import LoginForm, LogoutForm
from .timestamps import from_text, utc_now

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Checked against when the username doesn't exist, so a wrong username takes
# as long as a wrong password and response times don't reveal which accounts exist.
DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")

GENERIC_LOGIN_ERROR = "Incorrect username or password."


def temporary_password_expired(admin):
    if not admin["must_change_password"] or admin["temp_password_expires_at"] is None:
        return False
    return from_text(admin["temp_password_expires_at"]) < utc_now()


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        admin = get_db().execute(
            "SELECT * FROM admins WHERE username = ?", (form.username.data,)
        ).fetchone()
        stored_hash = admin["password_hash"] if admin else DUMMY_PASSWORD_HASH
        password_ok = check_password_hash(stored_hash, form.password.data)

        if admin is None or not password_ok:
            error = GENERIC_LOGIN_ERROR
        elif admin["disabled_at"] is not None:
            error = "This account is disabled. Contact whoever runs this Filingpoint server."
        elif temporary_password_expired(admin):
            error = "This temporary password has expired. Ask for a new one."
        else:
            log_in("admin", admin["id"])
            return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html", form=form, error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    form = LogoutForm()
    if form.validate_on_submit():
        log_out()
    return redirect(url_for("admin.login"))


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", logout_form=LogoutForm())
