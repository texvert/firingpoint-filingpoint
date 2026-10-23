# Filingpoint

[![Tests](https://github.com/texvert/firingpoint-filingpoint/actions/workflows/tests.yml/badge.svg)](https://github.com/texvert/firingpoint-filingpoint/actions/workflows/tests.yml)

A free, open-source and privacy-first equipment management system for target shooting clubs, covering asset tracking, allocation, and individual configuration history.

In case it wasn't obvious, the name Filingpoint is a play on the term *firing point*, where a shooter sets up their equipment on the range.

Filingpoint is designed to support GDPR compliance and to have minimal impact on a club's data-retention duties and policies, but I can't guarantee compliance. It is a training aid and asset management system, and is **not** a replacement for a club's existing legal responsibilities, such as maintaining an attendance register.

> **Status:** early development, working towards v0.1. Not yet ready for real club data.

## What it will do (v0.1)

- Keep a library of club jackets and slings, with sizing, condition and sling–jacket pairing
- Allocate equipment to users, with a full allocation history
- Record each user's settings on their equipment over time
- Let users view and export their own data

## Privacy by design

- **No personal details.** No names, contact details, ages or body measurements are stored. Users are pseudonymous IDs; the club keeps the ID-to-name lookup outside the system.
- **History belongs to the equipment.** Deleting a user removes their link to it while keeping the equipment's history. This is enforced by the database and covered by tests.
- **Retention limits** *(planned)*: data for returned equipment is reduced to month-level dates after 6 months and unlinked from the user after 12.

## Quick start (Docker)

```bash
git clone https://github.com/texvert/firingpoint-filingpoint.git
cd firingpoint-filingpoint
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"
# paste the output after FILINGPOINT_SECRET_KEY= in .env
docker compose up --build
```

Then open <http://127.0.0.1:8000>.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
flask --app filingpoint migrate
flask --app filingpoint run --debug
```

Run the tests with:

```bash
python -m pytest -v
```

## Licence

MIT. See [LICENSE](LICENSE).
