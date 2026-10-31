# Document Q&A

A web app for asking questions about uploaded PDFs. It retrieves relevant passages from selected files and generates a concise answer grounded in those passages.

## App features

- Register, log in, and keep a session across visits.
- Upload, select, and delete PDFs.
- Ask questions about selected files or compare two PDFs.
- Choose English or Arabic for each answer.
- View the files used as sources beneath the answer.
- Keep each user's files and vector data separate.

## AI features

- Extract PDF text, split it into chunks, and create embeddings when files are uploaded.
- Embed each question and retrieve relevant chunks from pgvector, limited to the selected PDFs.
- Generate answers from retrieved passages, with prompts that tell the model to acknowledge missing information instead of inventing it.
- Retrieve passages from both PDFs in parallel for question-based comparisons.
- Use language-specific prompts for English and Arabic answers.

## Project structure

```text
app/
  clients/       LLM providers, prompts, and vector database client
  controllers/   PDF processing, retrieval, and Q&A
  core/          Configuration, sessions, and startup
  models/        API schemas and database models/migrations
  routes/app/    Authentication, file, and Q&A endpoints
  static/        CSS and JavaScript
  templates/     Web interface
  main.py        FastAPI entry point
docker/          Compose stack and service configuration
```

## Technology

FastAPI, SQLAlchemy, Alembic, PostgreSQL with pgvector, Redis, PyMuPDF, HTML, CSS, and JavaScript. The generation and embedding providers are configured through environment variables.

## Setup

1. Copy each `docker/env/.env.example.*` file to the matching `docker/env/.env.*` name. Copy `docker/config/nginx/default.example.conf` to `default.conf` and `docker/config/prometheus/prometheus.yml.example` to `prometheus.yml` in the same directories.
2. Set the database credentials consistently in the app, Postgres, and exporter environment files. Set the model API keys, `CSRF_SECRET`, and Grafana credentials. Use the same metrics path in the app environment and Prometheus configuration.
3. Start the stack from the project root:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Open `http://localhost`. Database migrations run when the app container starts.
