# Full RAG App

Full RAG App is a FastAPI-based Retrieval Augmented Generation service for uploading documents, chunking them, indexing them in a vector database, retrieving relevant context, and generating grounded answers with an LLM provider.

The project also has two release lines:

- MongoDB release: the earlier release line, built around MongoDB-backed persistence.
- PostgreSQL release: the current release line in this repository, built around PostgreSQL, Alembic migrations, and pgvector.

## What It Does

- Upload text or PDF files for a user.
- Store users, assets, and chunks in PostgreSQL.
- Split uploaded files into chunks.
- Embed chunks with a configured embedding provider.
- Store/search vectors with PGVector or Qdrant client support.
- Retrieve relevant chunks for a query.
- Generate final answers with Groq, Google, or Hugging Face clients.
- Expose Prometheus metrics and a Docker monitoring stack.

## Stack

- API: FastAPI, Uvicorn
- Database: PostgreSQL with pgvector
- Migrations: Alembic
- Vector clients: PGVector and Qdrant client implementations
- LLM providers: Groq, Google GenAI, Hugging Face
- Observability: Prometheus, Grafana, Node Exporter, Postgres Exporter
- Container runtime: Docker Compose

## Project Layout

```text
app/
  clients/              LLM and vector database clients
  controllers/          Data, process, NLP, and user workflow logic
  fastapi_core/         Lifespan and metrics setup
  models/               Request schemas, DB schemas, enums, object models
  routes/               FastAPI route modules
  main.py               App entrypoint
docker/
  app/                  API Dockerfile, entrypoint, Alembic config template
  config/               Nginx and Prometheus config examples
  env/                  Safe env examples
  docker-compose.yml    Full deployment stack
run.sh                  Local helper script
```

## Configuration

Copy the example files and fill in real values locally:

```bash
cp app/.env.example app/.env
cp docker/env/.env.example.app docker/env/.env.app
cp docker/env/.env.example.postgres docker/env/.env.postgres
cp docker/env/.env.example.postgres-exporter docker/env/.env.postgres-exporter
cp docker/env/.env.example.grafana docker/env/.env.grafana
cp docker/config/nginx/default.example.conf docker/config/nginx/default.conf
cp docker/config/prometheus/prometheus.yml.example docker/config/prometheus/prometheus.yml
cp docker/app/alembic.example.ini docker/app/alembic.ini
```

Never commit live `.env` files, uploaded documents, database volumes, generated Alembic config, or monitoring runtime data. The `.gitignore` files are configured to keep those out of Git.

## Docker Deployment

From the repository root:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Useful URLs after startup:

```text
API docs:          http://127.0.0.1:8000/docs
Nginx proxy:       http://127.0.0.1/docs
Prometheus:        http://127.0.0.1:9090
Grafana:           http://127.0.0.1:3300
Postgres exporter: http://127.0.0.1:9187/metrics
```

PostgreSQL is published to the host on port `5434`. For tools such as DBeaver:

```text
Host: 127.0.0.1
Port: 5434
Database: full_rag_db
Username: value from docker/env/.env.postgres
Password: value from docker/env/.env.postgres
SSL: disable
```

Inside Docker, services connect to PostgreSQL with host `pgvector` and port `5432`.

## API Workflow

Base route:

```http
GET /api/v1/
```

Upload a document:

```http
POST /api/v1/data/upload/{user_name}
```

Process uploaded files into chunks:

```http
POST /api/v1/data/process/{user_name}
Content-Type: application/json

{
  "file_name": null,
  "chunk_size": 300,
  "overlap_size": 50,
  "do_reset": false
}
```

Push chunks into the vector database:

```http
POST /api/v1/nlp/push/{user_name}
Content-Type: application/json

{
  "do_reset": 0
}
```

Retrieve relevant chunks:

```http
POST /api/v1/nlp/retrieve/{user_name}
Content-Type: application/json

{
  "query": "What does this document say about deployment?",
  "limit": 5
}
```

Generate an answer:

```http
POST /api/v1/nlp/answer_user_query/{user_name}
Content-Type: application/json

{
  "query": "Summarize the main plan.",
  "limit": 5
}
```

## Local Development

Create and activate a Python environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r app\requirements.txt
```

Run the app from `app/` after configuring `app/.env`:

```bash
cd app
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Validation

Check Docker configuration:

```bash
docker compose -f docker/docker-compose.yml config
```

Check running services:

```bash
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs --tail=100 full-rag
```

Smoke-test the deployed app:

```bash
curl http://127.0.0.1:8000/docs
curl http://127.0.0.1/docs
curl http://127.0.0.1:9090/-/ready
```


## Inspiration

This project is inspired by the [Mini RAG Series by Abubakar on YouTube](https://www.youtube.com/playlist?list=PLvLvlVqNQGHCUR2p0b8a0QpVjDUg50wQj).

## Notes

- Existing Docker data volumes keep their original database initialization. If you change Postgres user, password, or database name after the volume exists, recreate the volume or migrate the database manually.
- Uploaded files and local vector/database stores are runtime data and should stay outside Git.
- The PostgreSQL release is the active deployment path in this repository; the MongoDB release is a separate earlier release line.
