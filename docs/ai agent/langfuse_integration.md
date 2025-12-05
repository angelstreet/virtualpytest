# Langfuse Integration

LLM Observability for the AI Agent System.

## What is Langfuse?

[Langfuse](https://langfuse.com) is an open-source LLM observability platform that tracks:
- **Token usage** (input/output per call)
- **Cost** (USD per request/session)
- **Latency** (response times)
- **Traces** (full agent execution flow)
- **Errors** (failures, rate limits)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent System                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐    │
│  │Explorer │  │ Builder  │  │ Executor │  │  Analyst  │    │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘    │
│       │            │             │              │           │
│       └────────────┴──────┬──────┴──────────────┘           │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │  Langfuse   │                          │
│                    │   Wrapper   │                          │
│                    └──────┬──────┘                          │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │   Langfuse    │
                    │   Dashboard   │
                    │  (port 3001)  │
                    └───────────────┘
```

## Setup Options

### Option 1: Self-Hosted (Free, Recommended)

Run Langfuse on your infrastructure. No data leaves your servers.

```bash
# Run the install script
./scripts/langfuse_install.sh
```

Access dashboard at: `http://localhost:3001`

### Option 2: Cloud (Quick Start)

1. Sign up at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Get your API keys from the dashboard
3. Configure `.env`:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Configuration

### Environment Variables

Add to `backend_server/.env`:

```bash
# Langfuse LLM Observability (auto-enabled when LANGFUSE_HOST is set)
# Self-hosted (after running langfuse_install.sh)
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key

# Cloud (alternative)
# LANGFUSE_HOST=https://cloud.langfuse.com
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
```

Add to `frontend/.env`:

```bash
# Local development - Direct access to Langfuse
VITE_LANGFUSE_URL=http://localhost:3001

# Production/Remote - Use SSL proxy on port 3002 (see Production Deployment section)
# VITE_LANGFUSE_URL=https://yourdomain.com:3002
```

### Access Method

**Langfuse opens in a new browser tab** (not embedded as iframe) to avoid CORS and path issues.

#### How It Works

1. Click "Langfuse" in navigation menu
2. Opens in new tab at configured URL
3. No CORS configuration needed
4. No iframe embedding issues

**Local Development:**
- Opens `http://localhost:3001` directly

**Production/Remote:**
- Opens `https://yourdomain.com:3002` via nginx SSL proxy

#### Production/Remote Deployment

**Problem:** Langfuse is a Next.js app that doesn't work well on subpaths like `/langfuse/`. When served at `https://yourdomain.com/langfuse/`, it generates broken asset URLs.

**Solution:** Expose Langfuse on a separate HTTPS port using nginx as an SSL proxy.

**Step 1: Add nginx SSL proxy on port 3002**

Add this to your nginx config (e.g., `/etc/nginx/sites-enabled/default`):

```nginx
# Langfuse SSL Proxy - Serves Langfuse at root path with HTTPS
server {
    listen 3002 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Step 2: Open firewall**

```bash
sudo ufw allow 3002/tcp
```

**Step 3: Reload nginx**

```bash
sudo nginx -t && sudo systemctl reload nginx
```

**Step 4: Configure frontend**

Update `frontend/.env`:

```bash
# Remote server
VITE_LANGFUSE_URL=https://yourdomain.com:3002

# Local development (unchanged)
# VITE_LANGFUSE_URL=http://localhost:3001
```

**Step 5: Rebuild frontend**

```bash
cd frontend
npm run build
# Restart your frontend service
```

**Why this works:**
- Langfuse runs on HTTP port 3001 internally
- nginx on port 3002 adds SSL and proxies to Langfuse
- Langfuse serves from root path `/` (not `/langfuse/`), so all asset URLs work
- Users click "Langfuse" → Opens in new tab at `https://yourdomain.com:3002`


### Enable/Disable

Langfuse is **auto-enabled** when `LANGFUSE_HOST` is configured. To disable:

```bash
# Remove or comment out LANGFUSE_HOST to disable
# LANGFUSE_HOST=http://localhost:3001
```

When disabled (no host configured), the system works normally without any Langfuse overhead.

## What Gets Tracked

| Metric | Description |
|--------|-------------|
| `input_tokens` | Tokens sent to Claude |
| `output_tokens` | Tokens generated by Claude |
| `cache_read_tokens` | Tokens read from prompt cache (90% cheaper) |
| `cache_create_tokens` | Tokens written to prompt cache |
| `duration_ms` | Response latency |
| `cost_usd` | Estimated cost per call |
| `agent_name` | Which agent made the call (Explorer, Builder, etc.) |
| `session_id` | Conversation session ID |
| `user_id` | User who initiated the request |

## Dashboard Features

Once enabled, access the Langfuse dashboard to see:

### Traces View
Full execution traces showing:
- QA Manager → Explorer → Builder flow
- Each tool call and result
- Token usage per step

### Analytics
- Daily/weekly token usage
- Cost breakdown by agent
- Latency percentiles
- Error rates

### Sessions
- Group traces by conversation
- See total cost per user session
- Identify expensive operations

## Pricing Comparison

| Setup | Monthly Cost | Data Location |
|-------|--------------|---------------|
| Self-hosted | **$0** | Your servers |
| Cloud Free | $0 (50k events) | Langfuse servers |
| Cloud Pro | $59+ | Langfuse servers |

## Troubleshooting

### Langfuse Not Connecting

```bash
# Check if Langfuse is running
docker ps | grep langfuse

# Check logs
docker logs langfuse-web

# Verify environment
echo $LANGFUSE_HOST
```

### No Data Showing

1. Verify `LANGFUSE_HOST` is set (this auto-enables Langfuse)
2. Check API keys are correct (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
3. Make an AI Agent request
4. Wait 10-30 seconds for data to appear

### Langfuse Opens But Shows Broken Page / 404 Errors

**Symptom:** Langfuse page loads but assets fail (404 errors for `/_next/static/...`)

**Cause:** Langfuse was accessed via subpath (e.g., `/langfuse/`) instead of root path

**Solution:** Use dedicated port with SSL proxy (see Production Deployment section):

```bash
# On remote server, access via port 3002 (not /langfuse/ subpath)
VITE_LANGFUSE_URL=https://yourdomain.com:3002
```

### SSL/HTTPS Errors on Remote Server

**Symptom:** `ERR_SSL_PROTOCOL_ERROR` when accessing `https://yourdomain.com:3001`

**Cause:** Port 3001 doesn't have SSL enabled

**Solution:** Use port 3002 with nginx SSL proxy (see Production Deployment):

```nginx
# nginx provides SSL on port 3002, proxies to HTTP port 3001
server {
    listen 3002 ssl;
    # ...
    location / {
        proxy_pass http://127.0.0.1:3001;
    }
}
```

### Port Conflict

If port 3001 is in use:

```bash
# Stop existing service
./scripts/langfuse_install.sh stop

# Edit docker-compose.yml
nano ~/.langfuse/docker-compose.yml
# Change "3001:3000" to "3002:3000"

# Restart
./scripts/langfuse_install.sh start

# Update .env files to use new port
VITE_LANGFUSE_URL=http://localhost:3002
LANGFUSE_HOST=http://localhost:3002
```

## Security

- **Self-hosted**: All data stays on your infrastructure
- **API keys**: Store in `.env`, never commit to git
- **Network**: Langfuse only needs outbound to your LLM provider
- **Firewall**: Only open port 3002 (SSL proxy), keep 3001 (Langfuse) internal
- **SSL**: Always use HTTPS in production (port 3002 provides this)

## Quick Reference

### Commands

```bash
# Install self-hosted Langfuse
./scripts/langfuse_install.sh

# Check status
./scripts/langfuse_install.sh status

# Stop Langfuse
./scripts/langfuse_install.sh stop

# Start Langfuse
./scripts/langfuse_install.sh start

# Uninstall completely
./scripts/langfuse_install.sh uninstall
```

### URLs

| Environment | Langfuse URL | Frontend URL |
|-------------|--------------|--------------|
| Local Dev | `http://localhost:3001` | `http://localhost:5073/langfuse-dashboard` |
| Production/Remote | `https://yourdomain.com:3002` | `https://yourdomain.com/langfuse-dashboard` |

**Note:** Production uses port 3002 (nginx SSL proxy) instead of subpath `/langfuse/` to avoid Next.js path issues.

### Files to Configure

| File | Purpose |
|------|---------|
| `backend_server/.env` | API keys, enable/disable |
| `frontend/.env` | Dashboard URL (opens in new tab) |
| `/etc/nginx/sites-enabled/default` | SSL proxy on port 3002 (production only) |
| `~/.langfuse/docker-compose.yml` | Docker configuration |

## Related

- [AI Agent Architecture](./ai_agentic.md)
- [Grafana Integration](/docs/integrations/grafana.md)

