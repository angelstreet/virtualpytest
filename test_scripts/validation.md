# validation

Validates all transitions in a navigation tree by testing each edge.

## Usage

```bash
python test_scripts/validation.py --userinterface horizon_android_mobile
python test_scripts/validation.py --max-iteration 10
python test_scripts/validation.py --edges "node1-node2,node2-node3"
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--userinterface` | string | `horizon_android_mobile` | UI interface name |
| `--max-iteration` | int | `0` | Max transitions to test (0 = all) |
| `--edges` | string | - | Comma-separated edge IDs to validate |

## Workflow

1. Loads optimal edge validation sequence
2. Executes each transition using pre-computed path
3. On failure: attempts recovery by navigating to home
4. Reports success rate and coverage percentage

