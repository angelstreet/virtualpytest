# kpi_measurement

Measures KPIs for a specific navigation edge by repeatedly executing the transition.

## Usage

```bash
python test_scripts/kpi_measurement.py --edge "live → live_fullscreen" --iterations 5
python test_scripts/kpi_measurement.py --edge "settings → home" --iterations 10
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--userinterface` | string | `horizon_android_mobile` | UI interface name |
| `--edge` | string | - | Action set label (e.g., "live → live_fullscreen") |
| `--iterations` | int | `3` | Number of measurement iterations |

## Workflow

1. Maps action_set label to from/to nodes
2. Navigates in loop: goto(from) → goto(to)
3. Waits 10 seconds for kpi_executor post-processing
4. Fetches KPI measurements from database
5. Displays min/max/avg statistics

## Output

Reports timing metrics (min, max, avg) for the measured transition.

