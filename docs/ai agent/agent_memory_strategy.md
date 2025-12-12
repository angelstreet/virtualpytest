# Agent Memory Strategy

How the AI agent maintains conversation context and memory between messages.

## Overview

The agent uses a **3-layer memory system** to maintain conversation context while being token-efficient:

| Layer | Content | Purpose |
|-------|---------|---------|
| **Context Injection** | interface, tree, host, device | Current working state |
| **Rolling Summary** | 3-line max | Older conversation history |
| **Recent Messages** | Last 1-2 turns | Immediate context |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ SYSTEM PROMPT                                                        │
│                                                                      │
│ You are Atlas, AI Assistant.                                        │
│                                                                      │
│ ## Current Context (use as defaults)                                │
│ - Interface: google_tv                                              │
│ - Tree ID: xxx-xxx-xxx                                              │
│ - Host: sunri-pi1                                                   │
│ - Device: device1                                                   │
│                                                                      │
│ ## Skills                                                           │
│ [available skills...]                                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ MESSAGE HISTORY                                                      │
│                                                                      │
│ User: "[Previous conversation summary]                               │
│        • navigate to watchlist... → Navigated to 'watchlist'        │
│        • goto shop... → Navigated to 'shop'"                        │
│ AI: "Understood. I have the context."                               │
│                                                                      │
│ User: "goto home"                     ← Last message                │
│ AI: "✅ Navigated to home"            ← Last response               │
│                                                                      │
│ User: "now show current node"         ← Current message             │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer 1: Context Injection

Key working parameters are extracted from tool calls and injected into the system prompt.

### Tracked Context Keys

- `userinterface_name` - Current UI being tested (e.g., `google_tv`)
- `tree_id` - Navigation tree identifier
- `host_name` - Host machine (e.g., `sunri-pi1`)
- `device_id` - Target device (e.g., `device1`)

### Context Extraction

Context is automatically extracted after successful calls to these tools:

```python
CONTEXT_TOOLS = {
    'navigate_to_node',
    'take_control',
    'click_element',
    'execute_device_action',
    'auto_discover_screen',
    'get_node_tree',
    'explore_navigation'
}
```

### Example

```
User: "navigate to watchlist on google_tv"
      ↓
Tool: navigate_to_node(userinterface_name='google_tv', tree_id='xxx')
      ↓
Context Updated: userinterface_name=google_tv, tree_id=xxx
      ↓
User: "goto shop"  ← No need to specify interface again!
```

## Layer 2: Rolling Summary

A 3-line rolling summary captures the essence of older conversation turns.

### Summary Format

```
• [user request brief] → [action taken]
• [user request brief] → [action taken]
• [user request brief] → [action taken]
```

### Example Summary

```
• navigate to watchlist... → Navigated to 'watchlist' on google_tv
• goto shop... → Navigated to 'shop'
• check current node... → Retrieved node info
```

### Summary Generation

After each turn, the summary is updated:

1. Extract key action from tool calls or response
2. Build summary line: `"• {user_brief} → {action_summary}"`
3. Append to existing summary
4. Keep only last 3 lines

## Layer 3: Recent Messages

Only the last 2 messages (1 user + 1 assistant) are sent in full.

### Why Only Last 2?

- User messages are typically short
- AI responses contain the final answer (no tool details)
- Combined with summary + context, this provides full picture

### What Gets Stored

| Type | Stored | Example |
|------|--------|---------|
| User message | Full text | `"navigate to watchlist on google_tv"` |
| AI response | Final text only | `"✅ Navigation completed"` |
| Tool calls | NOT stored | ~~`navigate_to_node(userinterface_name=...)`~~ |
| Tool results | NOT stored | ~~`{success: true, ...}`~~ |

## Token Efficiency

### Before (All Messages)

```
Turn 1: User: "navigate to watchlist" (30 tokens)
        AI: "✅ Done [Tools: navigate_to_node(...)]" (200 tokens)
Turn 2: User: "goto shop" (10 tokens)
        AI: "✅ Done [Tools: navigate_to_node(...)]" (200 tokens)
Turn 3: User: "show status" (10 tokens)
        AI: "Status: home node..." (100 tokens)
        
Total sent on Turn 4: ~550 tokens
```

### After (Summary + Last 2)

```
Summary: "• navigate... → watchlist
          • goto shop... → shop" (50 tokens)
Last turn: User + AI (110 tokens)
Current: User message (10 tokens)

Total sent on Turn 4: ~170 tokens (70% reduction)
```

## Implementation Details

### Session Context Storage

```python
# In session.py
class Session:
    context: Dict[str, Any] = field(default_factory=dict)
    # Keys:
    # - userinterface_name
    # - tree_id
    # - host_name
    # - device_id
    # - conversation_summary  ← Rolling summary
```

### Message Building (manager.py)

```python
# Build message history: summary + last 2 messages only
turn_messages = []
KEEP_LAST_N = 2  # 1 user + 1 assistant

# Prepend summary if available
summary = session.get_context('conversation_summary', '')
if summary and len(all_messages) > KEEP_LAST_N:
    turn_messages.append({
        "role": "user",
        "content": f"[Previous conversation summary]\n{summary}"
    })
    turn_messages.append({
        "role": "assistant", 
        "content": "Understood. I have the context."
    })

# Add last N messages
messages_to_add = all_messages[-KEEP_LAST_N:]
for msg in messages_to_add:
    turn_messages.append({"role": msg["role"], "content": msg["content"]})
```

### Summary Update (manager.py)

```python
def _update_conversation_summary(self, session, user_msg, ai_response, tool_calls):
    # Get existing summary
    existing = session.get_context('conversation_summary', '')
    
    # Build this turn's summary line
    if tool_calls:
        action_summary = f"Used {tool_calls[0]['tool_name']}"
    else:
        action_summary = ai_response[:50]
    
    new_line = f"• {user_msg[:30]}... → {action_summary}"
    
    # Combine, keep last 3 lines
    lines = existing.split('\n') + [new_line]
    session.set_context('conversation_summary', '\n'.join(lines[-3:]))
```

## Debugging

### Console Logs

```
[CONTEXT] Set userinterface_name=google_tv
[CONTEXT] Set tree_id=xxx-xxx-xxx
[SUMMARY] Updated: • navigate to watchlist... → Navigated to 'watchlist'
```

### Checking Session Context

```python
# In code
print(session.context)
# {'userinterface_name': 'google_tv', 'tree_id': 'xxx', 'conversation_summary': '...'}
```

## Best Practices

1. **Short user prompts** - Context is auto-filled, no need to repeat
2. **Trust the summary** - Older context is compressed but preserved
3. **Check context injection** - Key params appear in system prompt
4. **Monitor token usage** - Should be significantly reduced

## Related Files

- `backend_server/src/agent/core/manager.py` - Memory implementation
- `backend_server/src/agent/core/session.py` - Session storage
- `docs/ai agent/agent.md` - General agent architecture

