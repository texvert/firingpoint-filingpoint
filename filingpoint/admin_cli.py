import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .db import get_db
from .passwords import password_problem
from .usernames import username_problem


def prompt_for_password():
    while True:
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        problem = password_problem(password)
        if problem is None:
            return password
        click.echo(problem)


def ensure_organisation(db):
    row = db.execute("SELECT id FROM organisations ORDER BY id LIMIT 1").fetchone()
    if row is not None:
        return row["id"]
    name = click.prompt("No organisation exists yet. Organisation name")
    cursor = db.execute("INSERT INTO organisations (name) VALUES (?)", (name,))
    return cursor.lastrowid


@click.command("create-admin")
@click.option("--username", prompt=True, help="Login name for the new admin.")
@with_appcontext
def create_admin_command(username):
    """Create an admin account. Run this on the host machine."""
    db = get_db()
    if db.execute("PRAGMA user_version").fetchone()[0] == 0:
        raise click.ClickException(
            "The database isn't set up yet. Run 'flask --app filingpoint migrate' first."
        )
    problem = username_problem(username)
    if problem is not None:
        raise click.ClickException(problem)
    existing = db.execute(
        "SELECT 1 FROM admins WHERE username = ?", (username,)
    ).fetchone()
    if existing is not None:
        raise click.ClickException(f"An admin called '{username}' already exists.")

    organisation_id = ensure_organisation(db)
    password = prompt_for_password()
    db.execute(
        "INSERT INTO admins (organisation_id, username, password_hash) VALUES (?, ?, ?)",
        (organisation_id, username, generate_password_hash(password)),
    )
    db.commit()
    click.echo(f"Admin '{username}' created.")


def init_app(app):
    app.cli.add_command(create_admin_command)
