MIN_PASSWORD_LENGTH = 12


def password_problem(password):
    """Return a message explaining why a password is unacceptable, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return None
