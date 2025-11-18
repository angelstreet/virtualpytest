# Grafana Optional Deployment

Grafana is now a separate, optional container that can be enabled/disabled per server.

## Important: Configuration File

⚠️ **DO NOT EDIT `config.env.example`** - This is the template committed to git.

✅ **EDIT `config.env`** - This is your local configuration (git-ignored).

The setup script automatically copies `config.env.example` → `config.env` on first run.

## Changes Made

### 1. Configuration File (`config.env`)
Added new options:
```bash
# Grafana Configuration (optional)
ENABLE_GRAFANA=false
GRAFANA_PORT=3000
```

### 2. Setup Script (`setup.sh`)
- **Separated Grafana container** from `backend_server`
- **Conditional nginx config**: Only generates `/grafana/` location block if enabled
- **Conditional docker-compose**: Only adds `grafana` service if enabled
- **Conditional volumes**: Only creates Grafana volumes if enabled
- **Status display**: Shows Grafana status in configuration summary

### 3. Architecture Changes

#### Before (Integrated):
```
backend_server:
  - Port 5109 (API)
  - Port 3000 (Grafana)
  - Grafana volumes
  - Grafana environment variables
```

#### After (Separated):
```
backend_server:
  - Port 5109 (API only)

grafana: (optional)
  - Port 3000
  - Separate volumes
  - Independent container
  - Can be enabled/disabled per server
```

## Usage

### Enable Grafana on a Server

Edit `config.env`:
```bash
ENABLE_GRAFANA=true
```

Run setup:
```bash
./setup.sh
./launch.sh
```

Access Grafana:
```
https://api.virtualpytest.com/grafana
Credentials: admin / ${GRAFANA_ADMIN_PASSWORD}
```

### Disable Grafana on a Server

Edit `config.env`:
```bash
ENABLE_GRAFANA=false
```

Run setup:
```bash
./setup.sh
./launch.sh
```

Grafana container will not be created.

## Benefits

1. **Resource Savings**: Servers without Grafana use ~200MB less RAM
2. **Flexibility**: Each server can independently choose Grafana
3. **Clean Separation**: Monitoring is decoupled from core API
4. **Faster Deployment**: Servers without Grafana start faster

## Migration from Old Setup

If you have an existing server with integrated Grafana:

```bash
# 1. Stop containers
cd setup/docker/hetzner_custom
docker-compose --env-file ../../../.env -f docker-compose.yml down

# 2. Configure Grafana option
nano config.env
# Set: ENABLE_GRAFANA=true (or false)

# 3. Regenerate configs
./setup.sh

# 4. Restart
./launch.sh
```

## Notes

- **Grafana data persists** in named volumes even when disabled
- **Re-enabling Grafana** will restore previous data
- **Default password**: Set via `GRAFANA_ADMIN_PASSWORD` in main `.env` file
- **Official image**: Uses `grafana/grafana:latest` (official Grafana image)

