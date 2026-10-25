from werkzeug.security import check_password_hash

from filingpoint.db import get_db

GOOD_PASSWORD = "correct horse battery"


def run(app, *args, input=None):
    return app.test_cli_runner().invoke(args=list(args), input=input)


def test_create_admin_creates_organisation_and_stores_only_a_hash(app):
    result = run(
        app, "create-admin", "--username", "alice",
        input=f"Demo Club\n{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n",
    )
    assert result.exit_code == 0, result.output

    with app.app_context():
        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE username = 'alice'").fetchone()
        organisation = db.execute("SELECT name FROM organisations").fetchone()

    assert organisation["name"] == "Demo Club"
    assert admin["password_hash"] != GOOD_PASSWORD
    assert check_password_hash(admin["password_hash"], GOOD_PASSWORD)


def test_create_admin_rejects_a_short_password_then_accepts_a_long_one(app):
    result = run(
        app, "create-admin", "--username", "bob",
        input=f"Demo Club\nshort\nshort\n{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n",
    )
    assert result.exit_code == 0, result.output
    assert "at least 12 characters" in result.output


def test_create_admin_refuses_a_duplicate_username_in_any_case(app):
    run(app, "create-admin", "--username", "alice",
        input=f"Demo Club\n{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n")
    result = run(app, "create-admin", "--username", "ALICE")
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_create_admin_rejects_a_username_with_disallowed_characters(app):
    result = run(app, "create-admin", "--username", 'python -c "print(1)"')
    assert result.exit_code != 0
    assert "Usernames must be" in result.output
