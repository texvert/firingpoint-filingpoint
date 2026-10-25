import secrets
from datetime import timedelta

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .db import get_db
from .passwords import password_problem
from .timestamps import to_text, utc_now
from .usernames import username_problem

TEMP_PASSWORD_LIFETIME = timedelta(hours=48)


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


def find_admin(db, username):
    admin = db.execute(
        "SELECT * FROM admins WHERE username = ?", (username,)
    ).fetchone()
    if admin is None:
        raise click.ClickException(f"No admin called '{username}'.")
    return admin


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


@click.command("list-admins")
@with_appcontext
def list_admins_command():
    """List admin accounts and whether each is active."""
    admins = get_db().execute(
        "SELECT username, created_at, disabled_at FROM admins ORDER BY username"
    ).fetchall()
    if not admins:
        click.echo("No admin accounts yet. Create one with create-admin.")
        return
    for admin in admins:
        status = "disabled" if admin["disabled_at"] else "active"
        click.echo(f"{admin['username']:<32} {status:<9} created {admin['created_at']}")


@click.command("disable-admin")
@click.argument("username")
@with_appcontext
def disable_admin_command(username):
    """Stop an admin account from logging in."""
    db = get_db()
    find_admin(db, username)
    db.execute(
        "UPDATE admins SET disabled_at = ? WHERE username = ?",
        (to_text(utc_now()), username),
    )
    db.commit()
    click.echo(f"Admin '{username}' disabled.")


@click.command("enable-admin")
@click.argument("username")
@with_appcontext
def enable_admin_command(username):
    """Allow a disabled admin account to log in again."""
    db = get_db()
    find_admin(db, username)
    db.execute("UPDATE admins SET disabled_at = NULL WHERE username = ?", (username,))
    db.commit()
    click.echo(f"Admin '{username}' enabled.")


@click.command("reset-admin-password")
@click.argument("username")
@with_appcontext
def reset_admin_password_command(username):
    """Give an admin a temporary password that must be changed at next login."""
    db = get_db()
    find_admin(db, username)
    temporary_password = secrets.token_urlsafe(12)
    expires_at = utc_now() + TEMP_PASSWORD_LIFETIME
    db.execute(
        "UPDATE admins SET password_hash = ?, must_change_password = 1, "
        "temp_password_expires_at = ? WHERE username = ?",
        (generate_password_hash(temporary_password), to_text(expires_at), username),
    )
    db.commit()
    click.echo(f"Temporary password: {temporary_password}")
    click.echo(f"It expires at {to_text(expires_at)} (UTC) and must be changed at first login.")
    click.echo("It is shown only once and is not stored anywhere readable.")


def init_app(app):
    app.cli.add_command(create_admin_command)
    app.cli.add_command(list_admins_command)
    app.cli.add_command(disable_admin_command)
    app.cli.add_command(enable_admin_command)
    app.cli.add_command(reset_admin_password_command)
