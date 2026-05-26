#!/bin/bash
# ---------------------------------------------
# Running the Application with all dependecies
# ---------------------------------------------




set -e

echo "===================================="
echo " Starting MiniRAG Project"
echo "===================================="

# project dir
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APP_DIR="$PROJECT_ROOT/app"
DOCKER_DIR="$PROJECT_ROOT/docker"
DOCKER_COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

VENV_PATH="/mnt/d/Focus/_____Active_______/AI/venvs/rag_langchain_wsl/bin/activate"
FASTAPI_APP="main:app"
FASTAPI_HOST="127.0.0.1"
FASTAPI_PORT="8000"


echo "=== 1.0 Setup The Environment ==="
echo "- Project root: $PROJECT_ROOT"


echo ""
echo "- Checking Docker..."

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is not installed or not available."
    exit 1
fi

# 2. Start Docker Compose services
echo ""
echo "- Starting Docker services..."

cd "$DOCKER_DIR"

if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
else
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d
fi

echo "- Docker services started."


echo ""
echo "- Activating Python virtual environment..."

if [ ! -f "$VENV_PATH" ]; then
    echo "Error: virtual environment not found at:"
    echo "$VENV_PATH"
    exit 1
fi

source "$VENV_PATH"

echo "- Using Python:"
which python

# 4. Start FastAPI
echo ""
echo "- Starting FastAPI..."

cd "$APP_DIR"


echo "=== 1.0 Running The APP ==="
uvicorn "$FASTAPI_APP" --host "$FASTAPI_HOST" --port "$FASTAPI_PORT" --reload
