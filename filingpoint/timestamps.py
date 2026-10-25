from datetime import datetime, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now():
    return datetime.now(timezone.utc)


def to_text(moment):
    return moment.strftime(TIMESTAMP_FORMAT)


def from_text(text):
    return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
