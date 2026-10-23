import pytest

from filingpoint import create_app
from filingpoint.config import ConfigError


def test_production_refuses_to_start_without_secret_key(monkeypatch):
    monkeypatch.setenv("FILINGPOINT_ENV", "production")
    monkeypatch.delenv("FILINGPOINT_SECRET_KEY", raising=False)
    with pytest.raises(ConfigError):
        create_app()


def test_production_refuses_a_weak_secret_key(monkeypatch):
    monkeypatch.setenv("FILINGPOINT_ENV", "production")
    monkeypatch.setenv("FILINGPOINT_SECRET_KEY", "dev")
    with pytest.raises(ConfigError):
        create_app()


def test_production_accepts_a_strong_secret_key(monkeypatch, tmp_path):
    monkeypatch.setenv("FILINGPOINT_ENV", "production")
    monkeypatch.setenv("FILINGPOINT_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("FILINGPOINT_DATABASE", str(tmp_path / "prod.db"))
    app = create_app()
    assert app.config["SECRET_KEY"] == "x" * 64


def test_development_falls_back_to_dev_key(monkeypatch):
    monkeypatch.delenv("FILINGPOINT_ENV", raising=False)
    monkeypatch.delenv("FILINGPOINT_SECRET_KEY", raising=False)
    app = create_app({"TESTING": True})
    assert app.config["SECRET_KEY"] == "dev"
