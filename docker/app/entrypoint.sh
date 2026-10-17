#!/bin/bash
set -e

echo "----------------------------------------------------------"
echo "Running database migrations..."
cd /app/models/db_schemas/fullrag_db/

MIGRATION_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg/postgresql+psycopg2}"
sed -i "s|^sqlalchemy.url =.*|sqlalchemy.url = ${MIGRATION_DATABASE_URL}|" alembic.ini

alembic upgrade head
cd /app
echo "----------------------------------------------------------"

exec "$@"
