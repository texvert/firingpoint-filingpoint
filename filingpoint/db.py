import sqlite3
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate(db):
    current = db.execute("PRAGMA user_version").fetchone()[0]
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        number = int(path.name.split("_")[0])
        if number > current:
            db.executescript(path.read_text())
            db.execute(f"PRAGMA user_version = {number}")
            click.echo(f"Applied {path.name}")
    db.commit()


@click.command("migrate")
@with_appcontext
def migrate_command():
    migrate(get_db())
    click.echo("Database is up to date.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(migrate_command)

