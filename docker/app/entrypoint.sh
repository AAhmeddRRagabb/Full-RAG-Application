#!/bin/bash
set -e

echo "----------------------------------------------------------"
echo "Running database migrations..."
cd /app/models/db_schemas/fullrag_db/

DATABASE_URL="postgresql+psycopg2://${POSTGRES_USERNAME}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_MAIN_DB_NAME}"
sed -i "s|^sqlalchemy.url =.*|sqlalchemy.url = ${DATABASE_URL}|" alembic.ini

alembic upgrade head
cd /app
echo "----------------------------------------------------------"

exec "$@"
