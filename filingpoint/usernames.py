import re

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{3,32}")


def username_problem(username):
    """Return a message explaining why a username is unacceptable, or None."""
    if not USERNAME_PATTERN.fullmatch(username):
        return (
            "Usernames must be 3 to 32 characters, using only letters, "
            "numbers, dots, hyphens or underscores."
        )
    return None

