import os

from flask import Flask

from .config import load_config


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    load_config(app)
    if test_config is not None:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    from . import db
    db.init_app(app)

    @app.route("/")
    def index():
        return "Filingpoint is running."

    return app
