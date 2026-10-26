import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import load_config

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    load_config(app)
    if test_config is not None:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    csrf.init_app(app)

    from . import admin, admin_cli, auth, db
    db.init_app(app)
    admin_cli.init_app(app)
    auth.init_app(app)
    app.register_blueprint(admin.bp)

    @app.route("/")
    def index():
        return "Filingpoint is running."

    return app
