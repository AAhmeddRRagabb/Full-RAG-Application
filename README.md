# Full RAG App

A web chat application that answers questions using uploaded documents, web search, and conversation history. A query analyzer decides when current information or retrieval is needed; the answer model uses the available evidence to respond.

## Project Features

- Account registration and login with session authentication.
- Multiple chats per user: create, rename, delete, and revisit saved messages.
- Upload PDF or text files to a user account. Processing and vector indexing continue in the background after upload.
- Choose which uploaded files to use for each request and set answer depth to low, moderate, or high.
- Search selected files and the web when needed, then show source links alongside answers.
- Stream chat progress and the completed response; persist chat runs and their steps.
- CSRF checks on chat writes and logout, request rate limits, and Prometheus metrics.

## Project Structure

```text
app/
  clients/       LLM providers, prompt templates, and vector database client
  controllers/   Chat, data, user, and vector workflows
  core/          Settings, authentication, dependencies, and application startup
  models/        API schemas, database models, migrations, and enums
  routes/app/    Authentication, file, and chat endpoints
  static/        Frontend CSS and JavaScript
  templates/     Chat page
  main.py        FastAPI entry point
docker/          Compose stack, Dockerfile, service config, and env examples
run.sh           Docker startup script
```

## Project Technology

- **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, Alembic
- **Frontend:** HTML, CSS, JavaScript
- **Storage:** PostgreSQL with pgvector for documents and embeddings; Redis for sessions
- **AI and retrieval:** Groq, Google GenAI, or Hugging Face clients; Tavily web search
- **Deployment and monitoring:** Docker Compose, Nginx, Prometheus, Grafana

## Setup the Project

Docker is the simplest way to run the complete stack. From the project root, create the configuration files:

```bash
cp docker/env/.env.example.app docker/env/.env.app
cp docker/env/.env.example.postgres docker/env/.env.postgres
cp docker/env/.env.example.postgres-exporter docker/env/.env.postgres-exporter
cp docker/env/.env.example.grafana docker/env/.env.grafana
cp docker/config/nginx/default.example.conf docker/config/nginx/default.conf
cp docker/config/prometheus/prometheus.yml.example docker/config/prometheus/prometheus.yml
```

Set matching PostgreSQL credentials in the app and Postgres env files, replace `CSRF_SECRET`, and provide API keys for the configured model, embedding, and Tavily providers. Then start the stack:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

The app is available at `http://localhost` through Nginx or `http://localhost:8000` directly. API docs are at `http://localhost:8000/docs`. The container runs Alembic migrations at startup.

For local Python development, install `app/requirements.txt`, copy `app/.env.example` to `app/.env`, and run `uvicorn main:app --reload` from `app/`. PostgreSQL and Redis must also be running; apply the Alembic migrations under `app/models/db_schemas/fullrag_db` before starting the app.
