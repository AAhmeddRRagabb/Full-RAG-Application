#!/bin/bash
# ---------------------------------------------
# Running the Application with all dependecies
# ---------------------------------------------




set -e

echo "===================================="
echo " Starting FullRAG Project"
echo "===================================="

# project dir
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DOCKER_DIR="$PROJECT_ROOT/docker"
DOCKER_COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"


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

docker compose -f "$DOCKER_COMPOSE_FILE" up -d --build

echo "- FullRAG is available at http://localhost"
