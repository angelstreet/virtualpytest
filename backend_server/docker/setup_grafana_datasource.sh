#!/bin/bash
# Parse SUPABASE_DB_URI and generate Grafana datasource configuration
# Format: postgresql://user:password@host:port/database

set -e

echo "🔧 Setting up Grafana datasource from SUPABASE_DB_URI..."

# Check if SUPABASE_DB_URI is set
if [ -z "$SUPABASE_DB_URI" ]; then
    echo "❌ SUPABASE_DB_URI environment variable is not set"
    exit 1
fi

# Parse the connection string
# Format: postgresql://user:password@host:port/database
if [[ $SUPABASE_DB_URI =~ ^postgres(ql)?://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)$ ]]; then
    DB_USER="${BASH_REMATCH[2]}"
    DB_PASSWORD="${BASH_REMATCH[3]}"
    DB_HOST="${BASH_REMATCH[4]}"
    DB_PORT="${BASH_REMATCH[5]}"
    DB_NAME="${BASH_REMATCH[6]}"
    
    echo "✅ Parsed Supabase connection:"
    echo "   Host: $DB_HOST"
    echo "   Port: $DB_PORT"
    echo "   Database: $DB_NAME"
    echo "   User: $DB_USER"
    echo "   Password: [HIDDEN]"
else
    echo "❌ Failed to parse SUPABASE_DB_URI"
    echo "   Expected format: postgresql://user:password@host:port/database"
    echo "   Got: $SUPABASE_DB_URI"
    exit 1
fi

# Create the datasource configuration
DATASOURCE_FILE="/app/backend_server/config/grafana/provisioning/datasources/supabase.yaml"

cat > "$DATASOURCE_FILE" << EOF
# Grafana Datasource Provisioning (Auto-generated)
# Generated from SUPABASE_DB_URI environment variable

apiVersion: 1

datasources:
  - name: Supabase PostgreSQL
    type: postgres
    access: proxy
    url: ${DB_HOST}:${DB_PORT}
    database: ${DB_NAME}
    user: ${DB_USER}
    secureJsonData:
      password: ${DB_PASSWORD}
    jsonData:
      sslmode: 'require'
      postgresVersion: 1500
      timescaledb: false
      maxOpenConns: 10
      maxIdleConns: 2
      connMaxLifetime: 14400
    isDefault: true
    editable: false
    uid: supabase-postgres
EOF

echo "✅ Grafana datasource configuration created at $DATASOURCE_FILE"

