FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILINGPOINT_ENV=production \
    FILINGPOINT_DATABASE=/data/filingpoint.db

WORKDIR /app

RUN useradd --create-home filingpoint

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY filingpoint/ filingpoint/
COPY migrations/ migrations/

RUN mkdir -p /data /app/instance \
    && chown filingpoint:filingpoint /data /app/instance

USER filingpoint

EXPOSE 8000

CMD ["sh", "-c", "flask --app filingpoint migrate && exec gunicorn --workers 2 --bind 0.0.0.0:8000 'filingpoint:create_app()'"]

