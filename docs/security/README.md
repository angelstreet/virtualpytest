# Security Reports

Automated security analysis for VirtualPyTest backend components.

## View Reports

**[📊 Security Dashboard](./index.html)** - Interactive HTML report

**Raw Data:**
- [Host Report (JSON)](./host-report.json) - Backend host scan results
- [Server Report (JSON)](./server-report.json) - Backend server scan results
- [Frontend Report (JSON)](./frontend-report.json) - Frontend npm audit results

## Generate Reports

### Prerequisites

```bash
# Activate venv
source venv/bin/activate

# Install tools (included in backend_server/requirements.txt)
pip install bandit safety
```

### Run

```bash
# From project root
bash scripts/generate-security-docs.sh
```

### Output

Files generated in `docs/security/`:
- `index.html` - Interactive HTML dashboard
- `host-report.json` - Backend host Bandit results  
- `server-report.json` - Backend server Bandit results
- `frontend-report.json` - Frontend npm audit results

## What It Scans

| Component | Tool | Checks |
|-----------|------|--------|
| **backend_host/src/** | Bandit | Code vulnerabilities |
| **backend_server/src/** | Bandit | Code vulnerabilities |
| **frontend/** | npm audit | Dependency CVEs |
| **backend_host/requirements.txt** | Safety | Dependency CVEs |
| **backend_server/requirements.txt** | Safety | Dependency CVEs |

## Severity Levels

- 🔴 **HIGH** - Fix immediately
- 🟡 **MEDIUM** - Fix soon
- ⚪ **LOW** - Best practices

## Typical Workflow

```bash
# 1. Generate
bash scripts/generate-security-docs.sh

# 2. Review
open docs/security/index.html

# 3. Fix issues in code

# 4. Re-generate to verify
bash scripts/generate-security-docs.sh

# 5. Commit
git add docs/security/
git commit -m "chore: update security reports"
```

## Access

- **Local**: `docs/security/index.html`
- **Development**: `/docs/security/`
- **Production**: Served as static documentation

No frontend build needed - reports generated directly in docs!
