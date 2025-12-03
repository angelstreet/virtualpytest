# browser_task

Navigates to a URL and executes an AI-driven browser task using browser-use.

## Usage

```bash
python test_scripts/browser_task.py --url "google.com" --task "Search for Python tutorials"
python test_scripts/browser_task.py --url "youtube.com" --task "Find a video about cats"
python test_scripts/browser_task.py --url "amazon.com" --task "Search for headphones" --max_steps 15
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--url` | string | `youtube.com` | URL to navigate to |
| `--task` | string | `Launch funny cat video` | AI task description |
| `--max_steps` | int | `10` | Maximum steps for browser-use |

## Workflow

1. Opens browser if not already open
2. Navigates to specified URL
3. Waits 10 seconds for page load
4. Executes AI task via browser-use
5. Reports success/failure with execution logs

