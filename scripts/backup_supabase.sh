#!/bin/bash

set -e

# Use PostgreSQL 17 if available
if [ -d "/opt/homebrew/opt/postgresql@17/bin" ]; then
    export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/setup/db/backup"
ENV_FILE="$PROJECT_ROOT/.env"

# Load .env
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# Use SUPABASE_DB_URI if available, otherwise build from separate variables
if [ -n "$SUPABASE_DB_URI" ]; then
    DB_URL="$SUPABASE_DB_URI"
elif [ -n "$DATABASE_URL" ]; then
    DB_URL="$DATABASE_URL"
elif [ -n "$DB_HOST" ] && [ -n "$DB_NAME" ] && [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then
    [ -z "$DB_PORT" ] && DB_PORT=5432
    DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
else
    echo "❌ Missing DB credentials in .env"
    echo "   Required: SUPABASE_DB_URI or DATABASE_URL or (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)"
    exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
    echo "❌ pg_dump not found"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/supabase_backup_$TIMESTAMP.sql"

echo "Creating backup..."

# Use --no-sync for compatibility and ignore version mismatch warnings
export PGPASSWORD
if pg_dump "$DB_URL" --no-sync > "$BACKUP_FILE" 2>&1; then
    gzip "$BACKUP_FILE"
    echo "✅ Backup created: $BACKUP_FILE.gz"
else
    cat "$BACKUP_FILE"
    echo "❌ Backup failed - see error above"
    rm -f "$BACKUP_FILE"
    exit 1
fi

