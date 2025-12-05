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
# Langfuse LLM Observability (Optional)
# Set to true to enable token/cost tracking
LANGFUSE_ENABLED=false

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
# Langfuse Dashboard URL for iframe embedding
VITE_LANGFUSE_URL=http://localhost:3001
```

### CORS & Iframe Configuration

Langfuse is embedded in the frontend as an iframe. This requires proper CORS and Content Security Policy configuration.

#### Local Development

The system automatically configures CORS for local development:

**Docker Compose** (`~/.langfuse/docker-compose.yml`):
- Langfuse runs on `localhost:3001`
- CSP allows iframe embedding from `localhost:5073` (frontend)

**Nginx** (`backend_server/config/nginx/local.conf`):
```nginx
location /langfuse/ {
    # ... proxy settings ...
    
    # Allow iframe embedding for local development
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Content-Security-Policy "frame-ancestors 'self' http://localhost:5073" always;
}
```

**Frontend** (`vite.config.ts`):
```typescript
cors: {
  origin: true,
  credentials: true,
}
```

#### Production Deployment

For production, configure allowed domains in nginx:

**Nginx** (`backend_server/config/nginx/*.conf`):
```nginx
location /langfuse/ {
    # ... proxy settings ...
    
    # Allow iframe embedding from production domains
    add_header X-Frame-Options "ALLOW-FROM https://www.virtualpytest.com" always;
    add_header Content-Security-Policy "frame-ancestors 'self' https://www.virtualpytest.com https://virtualpytest.com https://virtualpytest.vercel.app" always;
}
```

After updating nginx config:
```bash
# Test configuration
sudo nginx -t

# Reload nginx (no downtime)
sudo systemctl reload nginx
```

#### Update Running Docker Container (Without Rebuild)

If Langfuse is already running and you need to update environment variables:

**Method 1: Edit docker-compose.yml and restart**
```bash
# Edit the compose file
nano ~/.langfuse/docker-compose.yml

# Add/modify environment variables under langfuse-server:
#   environment:
#     - CSP_ALLOW_IFRAME_SELF=true
#     - NEXT_PUBLIC_ENABLE_EXPERIMENTAL_FEATURES=false

# Restart container with new config
cd ~/.langfuse
docker compose down
docker compose up -d
```

**Method 2: Set environment variables directly (temporary)**
```bash
# Stop container
docker stop langfuse-web

# Start with new environment variables
docker start langfuse-web

# Or use docker update (limited variables)
docker update --env CSP_ALLOW_IFRAME_SELF=true langfuse-web
```

**Method 3: Reinstall (clean slate)**
```bash
# Uninstall
./scripts/langfuse_install.sh uninstall

# Reinstall (will have updated config)
./scripts/langfuse_install.sh
```

**Key Points:**
- `X-Frame-Options`: Controls which domains can embed Langfuse in iframes
- `Content-Security-Policy frame-ancestors`: Modern alternative to X-Frame-Options
- Add your domain to both directives
- Use `SAMEORIGIN` for same-domain embedding
- Use specific domains for cross-origin embedding
- **CORS is primarily handled by nginx**, not Langfuse itself

### Enable/Disable

Toggle observability without code changes:

```bash
# Enable
LANGFUSE_ENABLED=true

# Disable (default)
LANGFUSE_ENABLED=false
```

When disabled, the system works normally without any Langfuse overhead.

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

1. Verify `LANGFUSE_ENABLED=true`
2. Check API keys are correct
3. Make an AI Agent request
4. Wait 10-30 seconds for data to appear

### Iframe Not Loading / CORS Errors

**Symptom:** Blank iframe or browser console shows CORS errors

**Solution:**

1. **Check browser console** (F12) for errors like:
   - `Refused to frame because it set 'X-Frame-Options' to 'deny'`
   - `Refused to frame because an ancestor violates CSP`

2. **Verify nginx configuration:**
   ```bash
   # Check local config
   grep -A 5 "location /langfuse" backend_server/config/nginx/local.conf
   
   # Should show X-Frame-Options and CSP headers
   ```

3. **Restart nginx after config changes:**
   ```bash
   sudo systemctl restart nginx
   # OR for docker
   docker restart nginx
   ```

4. **For local development**, ensure frontend runs on `localhost:5073`:
   ```bash
   # Frontend should be accessible at
   http://localhost:5073/langfuse-dashboard
   ```

5. **Check Langfuse is accessible directly:**
   ```bash
   curl -I http://localhost:3001
   # Should return 200 OK
   ```

6. **Browser security:** Some browsers block mixed content (HTTP iframe in HTTPS page)
   - Solution: Use HTTPS for both or HTTP for both in local dev

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

- Self-hosted: All data stays on your infrastructure
- API keys: Store in `.env`, never commit to git
- Network: Langfuse only needs outbound to your Anthropic calls
- CORS: Restrict iframe embedding to trusted domains only

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
| Production | `https://yourdomain.com/langfuse/` | `https://yourdomain.com/langfuse-dashboard` |

### Files to Configure

| File | Purpose |
|------|---------|
| `backend_server/.env` | API keys, enable/disable |
| `frontend/.env` | Dashboard URL for iframe |
| `backend_server/config/nginx/*.conf` | CORS headers |
| `~/.langfuse/docker-compose.yml` | Docker configuration |

## Related

- [AI Agent Architecture](./ai_agentic.md)
- [Grafana Integration](/docs/integrations/grafana.md)

