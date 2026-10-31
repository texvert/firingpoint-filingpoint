from flask import Blueprint, g, redirect, render_template, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import admin_required, log_in, log_out, temporary_password_expired
from .db import get_db
from .forms import ChangePasswordForm, LoginForm, LogoutForm, NewPasswordForm

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Checked against when the username doesn't exist, so a wrong username takes
# as long as a wrong password and response times don't reveal which accounts exist.
DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")

GENERIC_LOGIN_ERROR = "Incorrect username or password."


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


@bp.route("/change-password", methods=["GET", "POST"])
@admin_required
def change_password():
    forced = bool(g.admin["must_change_password"])
    # A forced change follows a temporary-password login moments earlier, so we
    # don't ask for that password again. A voluntary change asks for the current one.
    form = NewPasswordForm() if forced else ChangePasswordForm()
    error = None
    if form.validate_on_submit():
        if not forced and not check_password_hash(
            g.admin["password_hash"], form.current_password.data
        ):
            error = "Your current password is incorrect."
        elif check_password_hash(g.admin["password_hash"], form.new_password.data):
            error = "Choose a password different from your current one."
        else:
            db = get_db()
            db.execute(
                "UPDATE admins SET password_hash = ?, must_change_password = 0, "
                "temp_password_expires_at = NULL WHERE id = ?",
                (generate_password_hash(form.new_password.data), g.admin["id"]),
            )
            db.commit()
            log_in("admin", g.admin["id"])
            return redirect(url_for("admin.dashboard"))
    return render_template(
        "admin/change_password.html",
        form=form,
        error=error,
        forced=forced,
        logout_form=LogoutForm(),
    )

@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", logout_form=LogoutForm())
