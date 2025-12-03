# Security Reports

Automated security analysis for VirtualPyTest backend components.

## View Reports

**[📊 Security Dashboard](./index.html)** - Interactive HTML report

**Raw Data:**
- [Host Report (JSON)](./host-report.json) - Backend host Bandit scan results
- [Server Report (JSON)](./server-report.json) - Backend server Bandit scan results
- [Frontend Report (JSON)](./frontend-report.json) - Frontend npm audit results
- [Snyk Host Report (JSON)](./snyk-host-report.json) - Backend host Snyk Code results
- [Snyk Server Report (JSON)](./snyk-server-report.json) - Backend server Snyk Code results

## Generate Reports

### Prerequisites

```bash
# Activate venv
source venv/bin/activate

# Install Python tools (included in backend_server/requirements.txt)
pip install bandit safety

# Install Snyk CLI (optional but recommended)
npm install -g snyk
snyk auth  # Login with free Snyk account
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
- `snyk-host-report.json` - Backend host Snyk Code results (SARIF)
- `snyk-server-report.json` - Backend server Snyk Code results (SARIF)

## What It Scans

| Component | Tool | Checks |
|-----------|------|--------|
| **backend_host/src/** | Bandit | Python code vulnerabilities |
| **backend_server/src/** | Bandit | Python code vulnerabilities |
| **backend_host/src/** | Snyk Code | SAST (Path Traversal, CORS, etc.) |
| **backend_server/src/** | Snyk Code | SAST (Path Traversal, CORS, etc.) |
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
