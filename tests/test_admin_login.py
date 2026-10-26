import pytest
from werkzeug.security import generate_password_hash

from filingpoint import create_app
from filingpoint.db import get_db, migrate

PASSWORD = "correct horse battery"


@pytest.fixture
def admin(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO organisations (id, name) VALUES (1, 'Demo Club')")
        db.execute(
            "INSERT INTO admins (organisation_id, username, password_hash) VALUES (1, ?, ?)",
            ("alice", generate_password_hash(PASSWORD)),
        )
        db.commit()


def log_in(client, username="alice", password=PASSWORD):
    return client.post(
        "/admin/login", data={"username": username, "password": password}
    )


def test_login_page_loads(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert b"Admin login" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_correct_password_logs_in(client, admin):
    response = log_in(client)
    assert response.status_code == 302
    assert client.get("/admin/").data.count(b"Logged in as alice") == 1


def test_wrong_password_and_unknown_user_give_the_same_error(client, admin):
    wrong_password = log_in(client, password="not the right one")
    unknown_user = log_in(client, username="mallory")
    assert b"Incorrect username or password." in wrong_password.data
    assert b"Incorrect username or password." in unknown_user.data
    assert client.get("/admin/").status_code == 302


def test_disabled_admin_cannot_log_in(app, client, admin):
    with app.app_context():
        get_db().execute("UPDATE admins SET disabled_at = '2026-01-01T00:00:00Z'")
        get_db().commit()
    response = log_in(client)
    assert b"This account is disabled." in response.data
    assert client.get("/admin/").status_code == 302


def test_disabling_an_admin_ends_their_current_session(app, client, admin):
    log_in(client)
    with app.app_context():
        get_db().execute("UPDATE admins SET disabled_at = '2026-01-01T00:00:00Z'")
        get_db().commit()
    assert client.get("/admin/").status_code == 302


def test_expired_temporary_password_is_refused(app, client, admin):
    with app.app_context():
        get_db().execute(
            "UPDATE admins SET must_change_password = 1, "
            "temp_password_expires_at = '2000-01-01T00:00:00Z'"
        )
        get_db().commit()
    response = log_in(client)
    assert b"temporary password has expired" in response.data


def test_logout_ends_the_session(client, admin):
    log_in(client)
    client.post("/admin/logout")
    assert client.get("/admin/").status_code == 302


def test_login_form_rejects_a_missing_csrf_token(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "csrf.db")})
    with app.app_context():
        migrate(get_db())
    response = app.test_client().post(
        "/admin/login", data={"username": "alice", "password": PASSWORD}
    )
    assert response.status_code == 400
