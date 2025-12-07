# Slack Integration Setup Guide

## Overview

The Slack integration allows you to sync AI Agent conversations from VirtualPyTest to your Slack workspace. Each conversation becomes a separate thread in a designated Slack channel, allowing your team to follow along with agent activities in real-time.

## Features

- ✅ **One-way sync** (VirtualPyTest → Slack)
- ✅ **Thread per conversation** (organized and searchable)
- ✅ **Agent nicknames** displayed in messages
- ✅ **Clean message format** (no tool calls/thinking by default)
- ✅ **No changes to AgentChat UI** (silent background sync)

## Setup Steps

### 1. Create Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name your app: `VirtualPyTest AI` (or any name)
4. Select your workspace
5. Click **"Create App"**

### 2. Configure Bot Permissions

1. In your app settings, go to **"OAuth & Permissions"**
2. Scroll to **"Bot Token Scopes"**
3. Add these scopes:
   - `chat:write` - Post messages to channels
   - `channels:read` - View channel list
   - `channels:history` - Read channel history (optional)

### 3. Install App to Workspace

1. Scroll up to **"OAuth Tokens for Your Workspace"**
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-...`)
   - ⚠️ Keep this token secret!

### 4. Create/Select Channel

1. In Slack, create a new channel: `#virtualpytest-ai`
2. Open channel details (click channel name)
3. Scroll down and copy the **Channel ID** (e.g., `C1234567890`)

### 5. Invite Bot to Channel

In your Slack channel, type:
```
/invite @VirtualPyTest AI
```

### 6. Configure in VirtualPyTest

1. Navigate to **Plugins → Slack** in VirtualPyTest
2. Enter your **Bot Token** (`xoxb-...`)
3. Enter your **Channel ID** (`C1234567890`)
4. Click **"Test Connection"** to verify
5. Toggle **"Enable Integration"** to ON
6. Click **"Save Configuration"**
7. Click **"Send Test Message"** to verify it works

## Configuration Options

### Basic Settings

| Setting | Description |
|---------|-------------|
| **Bot Token** | Your Slack bot OAuth token (starts with `xoxb-`) |
| **Channel ID** | The Slack channel where messages will be posted |
| **Enable Integration** | Toggle to enable/disable sync |

### Advanced Settings (Recommended: Keep disabled)

| Setting | Description | Recommended |
|---------|-------------|-------------|
| **Sync Tool Calls** | Include technical tool execution details | ❌ Disabled (too verbose) |
| **Sync Thinking** | Include AI reasoning/thinking process | ❌ Disabled (too verbose) |

## What Gets Synced?

### ✅ Synced to Slack:
- User questions
- Agent responses (final text only)
- Agent nicknames (Atlas, Sherlock, Scout, etc.)
- Conversation titles

### ❌ Not Synced (keeps Slack clean):
- Tool calls and technical details
- AI thinking/reasoning process
- Error messages (kept internal)
- Token/timing metrics

## Message Format

Conversations appear in Slack like this:

```
🤖 New AI Conversation: "Automate web app testing"
Conversation ID: abc12345... • 2025-01-15 14:30

  User: Automate web app testing for login page
  
  Atlas: I'll help you create automated tests for the login page...
  
  Sherlock: Web interface analyzed. Creating test cases for:
  - Login form validation
  - Successful login flow
  - Error handling
  
  Atlas: ✅ Created 3 test cases covering login functionality
```

## Troubleshooting

### "Channel not found"
- Verify the Channel ID is correct
- Check that it's a public channel or bot has been invited

### "Bot not in channel"
- Invite the bot: `/invite @YourBotName` in the Slack channel

### "Authentication failed"
- Verify the bot token starts with `xoxb-`
- Check token hasn't been revoked in Slack app settings
- Regenerate token if needed

### No messages appearing
- Check "Enable Integration" is toggled ON
- Verify configuration is saved
- Send a test message to verify connection
- Check backend logs: `journalctl -u backend_server -f | grep slack`

## Environment Variables (Optional)

If you prefer environment variables over the config file:

```bash
# Backend .env (optional - overrides config file)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890

# Frontend .env (optional - for workspace link)
VITE_SLACK_WORKSPACE_URL=https://your-team.slack.com
```

## Files Created

```
backend_server/
├── config/integrations/
│   ├── slack_config.json          # Configuration (created on save)
│   ├── slack_config.json.example  # Example template
│   └── slack_threads.json         # Thread mapping (auto-created)
├── src/
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── slack_sync.py          # Sync service
│   └── routes/
│       └── server_integrations_routes.py  # API routes (extended)

frontend/
└── src/pages/
    └── SlackIntegration.tsx       # UI configuration page
```

## API Endpoints

All endpoints are at `/server/integrations/slack/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config` | Get current configuration |
| POST | `/config` | Update configuration |
| POST | `/test` | Test connection |
| GET | `/status` | Get sync status & stats |
| POST | `/send-test` | Send test message to channel |

## Future Enhancements (Phase 2)

- 🔄 **Bi-directional sync** (Slack → AI responses)
- 💬 **Slash commands** (`/ai ask "..."`)
- 👥 **Team collaboration** (mentions, approvals)
- 📊 **Report sharing** directly to threads
- 🔔 **Custom notifications** (test failures, alerts)

## Security Notes

- ✅ Bot token stored server-side only (never exposed to frontend)
- ✅ Config file excluded from git (add to .gitignore)
- ✅ Permissions follow principle of least privilege
- ✅ API endpoints protected by authentication

## Support

For issues or questions:
1. Check backend logs: `journalctl -u backend_server | grep slack`
2. Review Slack app settings at [https://api.slack.com/apps](https://api.slack.com/apps)
3. Test connection in VirtualPyTest UI

