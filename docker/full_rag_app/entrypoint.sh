#!/bin/bash
set -e

echo "----------------------------------------------------------"
echo "Running database migrations..."
cd /final_app/models/db_schemas/minirag_db/
alembic upgrade head
cd /final_app
echo "----------------------------------------------------------"

exec "$@"
