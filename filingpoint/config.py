import os


def load_config(app):
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FILINGPOINT_SECRET_KEY", "dev"),
        DATABASE=os.environ.get(
            "FILINGPOINT_DATABASE",
            os.path.join(app.instance_path, "filingpoint.db"),
        ),
    )
