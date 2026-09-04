# Event Ticketing API

FastAPI backend for an event-ticketing platform.

Run the API from the repository root:

```bash
./.venv/bin/uvicorn main:app --reload
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

Configure the database with `DATABASE_URL` in `.env`. PostgreSQL is supported by
the existing `psycopg2` installation; a local SQLite database is used when no URL
is set. Set a long, unique `JWT_SECRET` before deploying.

Authentication endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/forgot-password`
- `PATCH /auth/reset-password`

`forgot-password` returns a reset token only as a development convenience. In
production, deliver that token through an email provider and omit it from the API
response.
