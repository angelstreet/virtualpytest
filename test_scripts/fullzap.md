# fullzap

Executes channel zap iterations with analysis (channel hopping test).

## Usage

```bash
python test_scripts/fullzap.py --max-iteration 5
python test_scripts/fullzap.py --action live_chup --goto-live true
python test_scripts/fullzap.py --audio-analysis true --max-iteration 10
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--userinterface` | string | `horizon_android_mobile` | UI interface name |
| `--max-iteration` | int | `3` | Number of zap iterations |
| `--action` | string | `live_chup` | Zap action to execute |
| `--goto-live` | bool | `true` | Navigate to live before zapping |
| `--audio-analysis` | bool | `false` | Enable audio analysis |

## Output

- Executes ZapExecutor workflow
- Prints zap summary table with timing per channel
- Reports total execution time and screenshot count

