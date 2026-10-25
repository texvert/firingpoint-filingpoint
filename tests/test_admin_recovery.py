from datetime import timedelta

from werkzeug.security import check_password_hash

from filingpoint.db import get_db
from filingpoint.timestamps import from_text, utc_now

GOOD_PASSWORD = "correct horse battery"


def run(app, *args, input=None):
    return app.test_cli_runner().invoke(args=list(args), input=input)


def make_admin(app, username="alice"):
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO organisations (id, name) VALUES (1, 'Demo Club')")
        db.commit()
    result = run(
        app, "create-admin", "--username", username,
        input=f"{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n",
    )
    assert result.exit_code == 0, result.output


def fetch_admin(app, username="alice"):
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()


def test_list_admins_shows_each_admin_and_status(app):
    make_admin(app, "alice")
    make_admin(app, "bob")
    run(app, "disable-admin", "bob")

    result = run(app, "list-admins")

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert "alice" in lines[0] and "active" in lines[0]
    assert "bob" in lines[1] and "disabled" in lines[1]


def test_disable_then_enable_admin(app):
    make_admin(app)

    run(app, "disable-admin", "alice")
    assert fetch_admin(app)["disabled_at"] is not None

    run(app, "enable-admin", "alice")
    assert fetch_admin(app)["disabled_at"] is None


def test_reset_admin_password_issues_a_working_temporary_password(app):
    make_admin(app)

    result = run(app, "reset-admin-password", "alice")

    assert result.exit_code == 0, result.output
    temporary_password = result.output.splitlines()[0].split(": ", 1)[1]
    admin = fetch_admin(app)
    assert check_password_hash(admin["password_hash"], temporary_password)
    assert not check_password_hash(admin["password_hash"], GOOD_PASSWORD)
    assert admin["must_change_password"] == 1
    expires = from_text(admin["temp_password_expires_at"])
    assert timedelta(hours=47) < expires - utc_now() <= timedelta(hours=48)


def test_recovery_commands_report_an_unknown_admin(app):
    for command in ("disable-admin", "enable-admin", "reset-admin-password"):
        result = run(app, command, "nobody")
        assert result.exit_code != 0
        assert "No admin called 'nobody'" in result.output
