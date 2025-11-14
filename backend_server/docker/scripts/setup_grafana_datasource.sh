#!/bin/bash
# Parse SUPABASE_DB_URI and generate Grafana datasource configuration
# Format: postgresql://user:password@host:port/database

set -e

echo "🔧 Setting up Grafana datasource from SUPABASE_DB_URI..."

# Check if SUPABASE_DB_URI is set
if [ -z "$SUPABASE_DB_URI" ]; then
    echo "⚠️ SUPABASE_DB_URI environment variable is not set"
    echo "⚠️ Grafana will start without Supabase datasource"
    echo "⚠️ You can add it manually in Grafana UI"
    exit 0  # Don't fail - allow Grafana to start
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
    echo "⚠️ Failed to parse SUPABASE_DB_URI"
    echo "   Expected format: postgresql://user:password@host:port/database"
    echo "   Got: $SUPABASE_DB_URI"
    echo "⚠️ Grafana will start without Supabase datasource"
    exit 0  # Don't fail - allow Grafana to start
fi

# Create the datasource configuration
DATASOURCE_FILE="/app/backend_server/config/grafana/provisioning/datasources/supabase.yaml"
DATASOURCE_DIR="$(dirname "$DATASOURCE_FILE")"

# Ensure directory exists
mkdir -p "$DATASOURCE_DIR"

# Resolve hostname to IPv4 address to avoid IPv6 issues on Render
echo "   Resolving hostname to IPv4..."
DB_IP=$(getent ahostsv4 "$DB_HOST" | head -1 | awk '{print $1}')
if [ -z "$DB_IP" ]; then
    echo "⚠️  Failed to resolve $DB_HOST to IPv4, using hostname directly"
    DB_IP="$DB_HOST"
else
    echo "   Resolved to IPv4: $DB_IP"
fi

cat > "$DATASOURCE_FILE" << EOF
# Grafana Datasource Provisioning (Auto-generated)
# Generated from SUPABASE_DB_URI environment variable

apiVersion: 1

datasources:
  - name: Supabase PostgreSQL
    type: postgres
    access: proxy
    url: ${DB_IP}:${DB_PORT}
    database: ${DB_NAME}
    user: ${DB_USER}
    secureJsonData:
      password: ${DB_PASSWORD}
    jsonData:
      database: ${DB_NAME}
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

# ============================================================================
# Configure grafana.ini dynamically from environment variables
# ============================================================================
echo ""
echo "🔧 Configuring Grafana settings from environment variables..."

GRAFANA_INI="/app/backend_server/config/grafana/grafana.ini"

# Set domain and root URL based on environment
if [ -n "$GF_SERVER_DOMAIN" ]; then
    DOMAIN="$GF_SERVER_DOMAIN"
    echo "   Domain: $DOMAIN (from GF_SERVER_DOMAIN)"
else
    # Default to api subdomain
    DOMAIN="api.virtualpytest.com"
    echo "⚠️  WARNING: GF_SERVER_DOMAIN environment variable is not set"
    echo "   Using default domain: $DOMAIN"
    echo "   Recommendation: Set GF_SERVER_DOMAIN in environment"
fi

# Set admin credentials from environment
ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-admin}"
echo "   Admin User: $ADMIN_USER"
echo "   Admin Password: [HIDDEN]"

# Set secret key from environment
SECRET_KEY="${GRAFANA_SECRET_KEY:-SW2YcwTIb9zpOOhoPsMm}"
echo "   Secret Key: [HIDDEN]"

# Configure CSRF trusted origins
CSRF_ORIGINS="$DOMAIN virtualpytest.com www.virtualpytest.com virtualpytest.onrender.com localhost:5073"
echo "   CSRF Trusted Origins: $CSRF_ORIGINS"

# Configure allowed iframe embedding domains
FRAME_ANCESTORS="${GRAFANA_FRAME_ANCESTORS:-https://www.virtualpytest.com https://virtualpytest.com https://virtualpytest.vercel.app https://*.vercel.app}"
echo "   Frame Ancestors (CSP): $FRAME_ANCESTORS"

# Update grafana.ini with sed (inline replacement)
# Server section
sed -i "s|^domain = .*|domain = $DOMAIN|g" "$GRAFANA_INI"
sed -i "s|^root_url = .*|root_url = %(protocol)s://%(domain)s/grafana/|g" "$GRAFANA_INI"

# Security section - uncomment and set values
sed -i "s|^;admin_user = .*|admin_user = $ADMIN_USER|g" "$GRAFANA_INI"
sed -i "s|^admin_user = .*|admin_user = $ADMIN_USER|g" "$GRAFANA_INI"
sed -i "s|^;admin_password = .*|admin_password = $ADMIN_PASSWORD|g" "$GRAFANA_INI"
sed -i "s|^admin_password = .*|admin_password = $ADMIN_PASSWORD|g" "$GRAFANA_INI"
sed -i "s|^;secret_key = .*|secret_key = $SECRET_KEY|g" "$GRAFANA_INI"
sed -i "s|^secret_key = .*|secret_key = $SECRET_KEY|g" "$GRAFANA_INI"

# Cookie settings for cross-origin
sed -i "s|^cookie_secure = .*|cookie_secure = true|g" "$GRAFANA_INI"
sed -i "s|^cookie_samesite = .*|cookie_samesite = none|g" "$GRAFANA_INI"

# CSRF trusted origins
sed -i "s|^csrf_trusted_origins = .*|csrf_trusted_origins = $CSRF_ORIGINS|g" "$GRAFANA_INI"

# Enable CSP for iframe embedding
sed -i "s|^;content_security_policy = false|content_security_policy = true|g" "$GRAFANA_INI"
sed -i "s|^content_security_policy = false|content_security_policy = true|g" "$GRAFANA_INI"

# Add frame-ancestors to CSP template to allow iframe embedding
CSP_TEMPLATE="script-src 'self' 'unsafe-eval' 'unsafe-inline' 'strict-dynamic' \$NONCE;object-src 'none';font-src 'self';style-src 'self' 'unsafe-inline' blob:;img-src * data:;base-uri 'self';connect-src 'self' grafana.com ws://\$ROOT_PATH wss://\$ROOT_PATH;manifest-src 'self';media-src 'none';form-action 'self';frame-ancestors 'self' $FRAME_ANCESTORS;"
sed -i "s|^;content_security_policy_template = .*|content_security_policy_template = \"\"\"$CSP_TEMPLATE\"\"\"|g" "$GRAFANA_INI"
sed -i "s|^content_security_policy_template = .*|content_security_policy_template = \"\"\"$CSP_TEMPLATE\"\"\"|g" "$GRAFANA_INI"

# Enable anonymous access for embedded dashboards (reduces auth warnings)
sed -i "s|^;enabled = false|enabled = true|g" "$GRAFANA_INI" 
sed -i "s|^\[auth.anonymous\]|[auth.anonymous]\nenabled = true|g" "$GRAFANA_INI"
sed -i "/^\[auth.anonymous\]/a org_name = Main Org." "$GRAFANA_INI"
sed -i "/^\[auth.anonymous\]/a org_role = Viewer" "$GRAFANA_INI"

# Disable Grafana Live (WebSocket) to prevent 404 errors in logs
sed -i "s|^;max_connections = 100|max_connections = 0|g" "$GRAFANA_INI"
sed -i "s|^max_connections = 100|max_connections = 0|g" "$GRAFANA_INI"

echo "✅ Grafana configuration updated dynamically"
echo "   CSP enabled with frame-ancestors for iframe embedding"
echo "   Anonymous access enabled for embedded dashboards"
echo "   Grafana Live disabled (no real-time updates)"


