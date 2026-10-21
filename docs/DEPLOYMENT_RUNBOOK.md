# Deployment and operations runbook

## Configuration

Use `.env.example`; never commit `.env`. Production requires a long random `SECRET_KEY` and a MySQL `DATABASE_URL`.

## Release

1. Back up MySQL with `mysqldump butcherbridge > backup.sql`.
2. Install locked requirements in a virtual environment.
3. Run `FLASK_APP=wsgi:app flask db upgrade`.
4. Run the automated test suite.
5. Start `gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app` behind Nginx/TLS.
6. Check `/health`, login, load a scenario and run one evaluation.

## Rollback

Stop the new service, run `flask db downgrade -1` only when the migration release notes confirm it is safe, deploy the previous application version and restore the MySQL dump if data compatibility requires it.

## Monitoring and retention

- Capture application stdout/stderr with the hosting service or systemd.
- Alert on repeated HTTP 500 responses and failed health checks.
- Retain operational error logs for 14 days.
- Take daily encrypted MySQL backups and test restoration monthly.
- Restrict the repository and deployed application to authorised participants.

