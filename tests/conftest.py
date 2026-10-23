import pytest

from filingpoint import create_app
from filingpoint.db import get_db, migrate


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    with app.app_context():
        migrate(get_db())
    yield app


@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()
