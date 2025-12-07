# Slack Integration

## Overview

Slack integration syncs AI Agent conversations from VirtualPyTest to your Slack workspace. Each conversation appears as a separate thread in a designated channel.

## Architecture

Follows the same pattern as JIRA integration:
- **Configuration**: JSON file (`config/integrations/slack_config.json`)
- **Routes**: Extended `server_integrations_routes.py`
- **UI**: React page at `/integrations/slack`
- **No environment variables needed**

## Quick Start

1. **Create Slack App** at https://api.slack.com/apps
2. **Add Bot Scopes**: `chat:write`, `channels:read`
3. **Install to Workspace** and copy bot token (`xoxb-...`)
4. **Get Channel ID** from Slack channel details
5. **Configure in UI**: Navigate to `Plugins → Slack`
6. **Test & Enable**: Test connection, then toggle enable

## Configuration Format

```json
{
  "enabled": true,
  "bot_token": "xoxb-...",
  "channel_id": "C1234567890",
  "sync_tool_calls": false,
  "sync_thinking": false
}
```

**Stored in**: `backend_server/config/integrations/slack_config.json` (gitignored)

## Message Flow

```
User message in AgentChat
    ↓
Backend (silent sync)
    ↓
Slack Service → Posts to channel thread
    ↓
Team views in Slack (read-only)
```

## What Gets Synced

✅ **Synced:**
- User questions
- Agent responses (final text)
- Agent nicknames (Atlas, Sherlock, Scout, etc.)
- Conversation titles

❌ **Not Synced** (keeps Slack clean):
- Tool calls (too verbose)
- AI reasoning (too verbose)
- Error messages (internal only)
- Metrics (tokens, timing)

## API Endpoints

All at `/server/integrations/slack/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config` | GET | Get configuration |
| `/config` | POST | Update configuration |
| `/test` | POST | Test connection |
| `/status` | GET | Get sync status |
| `/send-test` | POST | Send test message |

## Files

```
backend_server/
├── config/integrations/
│   ├── slack_config.json           # Configuration (gitignored)
│   ├── slack_config.json.example   # Template
│   ├── slack_threads.json          # Thread mapping (auto-created)
│   └── SLACK_SETUP.md              # Detailed setup guide
├── src/
│   ├── integrations/
│   │   └── slack_sync.py           # Background sync service
│   └── routes/
│       └── server_integrations_routes.py  # API routes

frontend/src/pages/
└── SlackIntegration.tsx            # Configuration UI
```

## Example Slack Thread

```
🤖 Automate web app testing
Conversation ID: abc12345... • 2025-01-15 14:30

User: Automate web app testing for login page

Atlas: I'll help you create automated tests...

Sherlock: Web interface analyzed. Creating test cases...

Atlas: ✅ Created 3 test cases for login functionality
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| Channel not found | Verify Channel ID |
| Bot not in channel | Invite bot: `/invite @BotName` |
| Authentication failed | Check bot token (starts with `xoxb-`) |
| No messages | Enable integration in UI |

## Future Enhancements

- 🔄 Bi-directional sync (Phase 2)
- 💬 Slack slash commands
- 👥 Team collaboration features
- 📊 Report sharing

## Security

- ✅ Credentials in JSON config (gitignored)
- ✅ Bot token never exposed to frontend
- ✅ Same security pattern as JIRA integration
- ✅ API endpoints protected by authentication

