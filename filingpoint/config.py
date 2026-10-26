import os
from datetime import timedelta

MIN_SECRET_KEY_LENGTH = 32


class ConfigError(RuntimeError):
    pass


def load_config(app):
    env = os.environ.get("FILINGPOINT_ENV", "development")
    secret_key = os.environ.get("FILINGPOINT_SECRET_KEY")

    if env == "production":
        if not secret_key or len(secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ConfigError(
                "FILINGPOINT_SECRET_KEY must be set to a random value of at least "
                f"{MIN_SECRET_KEY_LENGTH} characters when FILINGPOINT_ENV=production"
            )

    app.config.from_mapping(
        FILINGPOINT_ENV=env,
        SECRET_KEY=secret_key or "dev",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(env == "production"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        DATABASE=os.environ.get(
            "FILINGPOINT_DATABASE",
            os.path.join(app.instance_path, "filingpoint.db"),
        ),
    )
