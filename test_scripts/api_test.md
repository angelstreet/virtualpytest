# api_test

Tests API endpoints and validates responses.

## Usage

```bash
python test_scripts/api_test.py --profile sanity          # Quick health check
python test_scripts/api_test.py --profile full            # Full API validation
python test_scripts/api_test.py --endpoints "/health,/devices/getAllDevices"
python test_scripts/api_test.py --spec server-device-management
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--profile` | string | `sanity` | Predefined profile (sanity, full) |
| `--endpoints` | string | - | Custom comma-separated endpoint list |
| `--spec` | string | - | OpenAPI spec name to test |

## Output

- Tests each endpoint and records success/failure
- Reports response times and status codes
- Calculates success rate percentage

