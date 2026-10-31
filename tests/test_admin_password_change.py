import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from filingpoint.db import get_db

TEMP_PASSWORD = "temporary-pass-123"
NEW_PASSWORD = "a brand new passphrase"


@pytest.fixture
def temp_admin(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO organisations (id, name) VALUES (1, 'Demo Club')")
        db.execute(
            "INSERT INTO admins (organisation_id, username, password_hash, "
            "must_change_password, temp_password_expires_at) "
            "VALUES (1, 'alice', ?, 1, '2999-01-01T00:00:00Z')",
            (generate_password_hash(TEMP_PASSWORD),),
        )
        db.commit()


def fetch_admin(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM admins WHERE username = 'alice'").fetchone()


def log_in(client, password=TEMP_PASSWORD):
    return client.post("/admin/login", data={"username": "alice", "password": password})


def change(client, new=NEW_PASSWORD, confirm=None, current=None):
    data = {"new_password": new, "confirm_password": new if confirm is None else confirm}
    if current is not None:
        data["current_password"] = current
    return client.post("/admin/change-password", data=data)

def test_temporary_password_login_is_forced_to_change_password(client, temp_admin):
    log_in(client)
    response = client.get("/admin/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/change-password")


def test_changing_password_clears_the_flag_and_unlocks_the_dashboard(app, client, temp_admin):
    log_in(client)
    response = change(client)
    assert response.status_code == 302

    admin = fetch_admin(app)
    assert admin["must_change_password"] == 0
    assert admin["temp_password_expires_at"] is None
    assert check_password_hash(admin["password_hash"], NEW_PASSWORD)
    assert b"Logged in as alice" in client.get("/admin/").data


def test_short_new_password_is_refused(app, client, temp_admin):
    log_in(client)
    response = change(client, new="short")
    assert b"at least 12 characters" in response.data
    assert fetch_admin(app)["must_change_password"] == 1


def test_mismatched_confirmation_is_refused(client, temp_admin):
    log_in(client)
    response = change(client, confirm="something else entirely")
    assert b"don&#39;t match" in response.data


def test_forced_change_does_not_ask_for_the_current_password(client, temp_admin):
    log_in(client)
    page = client.get("/admin/change-password")
    assert b"Current password" not in page.data


def test_voluntary_change_asks_for_and_checks_the_current_password(client, temp_admin):
    log_in(client)
    change(client)
    page = client.get("/admin/change-password")
    assert b"Current password" in page.data

    response = change(client, new="another fresh passphrase", current="wrong password here")
    assert b"current password is incorrect" in response.data

    response = change(client, new="another fresh passphrase", current=NEW_PASSWORD)
    assert response.status_code == 302

def test_reusing_the_same_password_is_refused(client, temp_admin):
    log_in(client)
    response = change(client, new=TEMP_PASSWORD)
    assert b"different from your current one" in response.data


def test_session_ends_if_temporary_password_expires_mid_session(app, client, temp_admin):
    log_in(client)
    with app.app_context():
        get_db().execute("UPDATE admins SET temp_password_expires_at = '2000-01-01T00:00:00Z'")
        get_db().commit()
    response = client.get("/admin/change-password")
    assert response.headers["Location"].endswith("/admin/login")
