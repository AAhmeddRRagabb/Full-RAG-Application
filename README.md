# Document Q&A

A small web app for asking questions about your uploaded PDFs. It retrieves relevant PDF passages and generates one answer with page sources.

## Features

- Register, log in, and keep your session.
- Upload and delete PDFs. Upload finishes after text extraction and vector indexing.
- Select which PDFs to use for a question.
- Get one answer grounded in retrieved PDF passages, with file and page references.
- Keep each user's files and vector data separate.

## Project Structure

```text
app/
  clients/       Model providers, prompt template, and pgvector client
  controllers/   PDF preparation, retrieval, and Q&A
  core/          Settings, authentication, and startup
  models/        API and database schemas, migrations
  routes/app/    Authentication, file, and Q&A endpoints
  static/        CSS and JavaScript
  templates/     Single-page interface
  main.py        FastAPI entry point
docker/          Compose stack and service configuration
```

## Technology

Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL with pgvector, Redis, PyMuPDF, HTML, CSS, and JavaScript. The answer and embedding providers are selected in the app environment file.

## Setup

Copy the example environment files and configure PostgreSQL, Redis, a generation provider, an embedding provider, and `CSRF_SECRET`. Then start the stack:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

The app is available through Nginx at `http://localhost`. For local development, install `app/requirements.txt`, copy `app/.env.example` to `app/.env`, run the Alembic migrations, and start `uvicorn main:app --reload` from `app/`.

The new migration removes saved chats, messages, runs, and run steps. Back up the database first if you need that history.
