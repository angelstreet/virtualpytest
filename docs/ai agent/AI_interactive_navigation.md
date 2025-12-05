# AI Interactive Navigation System

This document describes the AI-driven page navigation and element interaction system in VirtualPyTest.

---

## Overview

The AI Interactive Navigation system allows the AI agent to **control the user's browser** within the React application. Instead of just answering questions, the AI can:

- Navigate to any page
- Interact with UI elements (click, filter, select)
- Highlight elements to draw attention
- Show toast notifications

This creates a true "co-pilot" experience where the AI can demonstrate, guide, and automate UI tasks.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     USER        │────▶│   AI BACKEND    │────▶│    FRONTEND     │
│  "go to reports"│     │   (Claude)      │     │  (React App)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               │  1. AI calls tool      │
                               │  navigate_to_page()    │
                               │                        │
                               │  2. Tool emits         │
                               │  WebSocket event       │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ SocketManager   │────▶│   AIContext     │
                        │ (Backend)       │     │   (Frontend)    │
                        └─────────────────┘     └─────────────────┘
                                                        │
                                                        │ 3. Context calls
                                                        │ navigate()
                                                        ▼
                                                ┌─────────────────┐
                                                │  React Router   │
                                                │  Page Changes   │
                                                └─────────────────┘
```

---

## Page Schema System

### What is it?

A registry that defines **what elements are controllable** on each page. The AI can query this schema to understand available actions without hard-coding each one.

### Location

```
frontend/src/lib/ai/pageSchema.ts
```

### Schema Structure

```typescript
interface PageSchema {
  path: string;           // Route path (e.g., '/device-control')
  name: string;           // Display name
  description: string;    // What the page does
  elements: PageElement[];// Controllable elements
  quickActions?: string[];// Common AI shortcuts
}

interface PageElement {
  id: string;             // Unique element ID
  type: string;           // button, table, dropdown, grid, modal, etc.
  label: string;          // Human-readable label
  actions: string[];      // Available actions (click, select, filter...)
  params?: Record<string, string>; // Action parameters
}
```

### Registered Pages

| Path | Name | Key Elements |
|------|------|--------------|
| `/` | Dashboard | host-accordion, refresh-btn, restart-service-btn |
| `/device-control` | Device Control | device-grid, host-filter, stream-modal |
| `/test-execution/run-tests` | Run Tests | host-selector, device-selector, run-btn |
| `/test-execution/run-campaigns` | Run Campaigns | campaign-stepper, launch-btn |
| `/test-plan/test-cases` | Test Cases | testcase-table, create-btn, search-input |
| `/test-plan/campaigns` | Campaigns | campaign-table, create-btn |
| `/monitoring/incidents` | Incidents | active-alerts-table, freeze-modal |
| `/monitoring/heatmap` | Heatmap | mosaic-player, timeline-slider, analysis-table |
| `/test-results/reports` | Test Reports | reports-table, detail-toggle |
| `/test-results/campaign-reports` | Campaign Reports | campaign-reports-table, trend-chart |
| `/builder/test-builder` | Test Builder | step-canvas, action-palette, device-preview |
| `/configuration/settings` | Settings | settings-form, save-btn |
| `/ai-agent` | AI Agent Chat | chat-input, chat-history, mode-selector |

---

## Backend Tools

### Location

```
backend_server/src/agent/tools/page_interaction.py
```

### Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_available_pages()` | Lists all navigable pages | None |
| `get_page_schema(page_path)` | Returns elements on a specific page | `page_path: string` |
| `navigate_to_page(page_name, context?)` | Navigate browser to a page | `page_name: string`, `context?: object` |
| `interact_with_element(element_id, action, params?)` | Interact with an element | `element_id`, `action`, `params?` |
| `highlight_element(element_id, duration_ms?)` | Highlight an element | `element_id`, `duration_ms` |
| `show_toast(message, severity?)` | Show a notification | `message`, `severity` |

### Navigation Aliases

The `navigate_to_page` tool supports natural language page names:

| Alias | Path |
|-------|------|
| `dashboard`, `home` | `/` |
| `device control`, `devices`, `rec`, `streams` | `/device-control` |
| `run tests`, `execute tests`, `test execution` | `/test-execution/run-tests` |
| `run campaigns` | `/test-execution/run-campaigns` |
| `test cases`, `testcases` | `/test-plan/test-cases` |
| `campaigns` | `/test-plan/campaigns` |
| `incidents`, `alerts` | `/monitoring/incidents` |
| `heatmap`, `monitoring` | `/monitoring/heatmap` |
| `reports`, `test reports` | `/test-results/reports` |
| `campaign reports` | `/test-results/campaign-reports` |
| `test builder`, `builder` | `/builder/test-builder` |
| `settings`, `config` | `/configuration/settings` |
| `ai agent`, `chat` | `/ai-agent` |

---

## Frontend Integration

### AIContext Event Handling

The `AIContext` (`frontend/src/contexts/AIContext.tsx`) listens for WebSocket events and dispatches actions:

```typescript
socket.on('ui_action', (event) => {
  // Navigation
  if (event.action === 'navigate') {
    navigate(event.payload.path);
  }
  
  // Element Interaction
  if (event.action === 'interact') {
    window.dispatchEvent(new CustomEvent('ai-interact', { 
      detail: event.payload 
    }));
  }
  
  // Highlight
  if (event.action === 'highlight') {
    window.dispatchEvent(new CustomEvent('ai-highlight', { 
      detail: event.payload 
    }));
  }
  
  // Toast
  if (event.action === 'toast') {
    window.dispatchEvent(new CustomEvent('ai-toast', { 
      detail: event.payload 
    }));
  }
});
```

### useAIControllable Hook

Components can register themselves as AI-controllable using this hook:

**Location:** `frontend/src/hooks/ai/useAIControllable.ts`

**Usage:**

```tsx
import { useAIControllable } from '../hooks/ai';

const RunButton = () => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  useAIControllable({
    elementId: 'run-btn',      // Must match pageSchema
    ref: buttonRef,             // For auto-highlight
    onAction: (action, params) => {
      if (action === 'click') {
        handleRunClick();
      }
    }
  });
  
  return <button ref={buttonRef}>Run Test</button>;
};
```

**Features:**
- `onAction(action, params)` - Called when AI interacts with the element
- `onHighlight(duration_ms)` - Custom highlight behavior (optional)
- `ref` - DOM reference for default highlight (blue glow + scroll into view)

### useAIToastListener Hook

Connect AI toast events to your toast provider:

```tsx
import { useAIToastListener } from '../hooks/ai';

const ToastProvider = ({ children }) => {
  const { showToast } = useToast();
  
  useAIToastListener(showToast); // Connects AI → Toast system
  
  return <>{children}</>;
};
```

---

## Event Flow Examples

### Example 1: Navigation

```
User: "go to heatmap"
    ↓
AI (Claude): Detects navigation intent
    ↓
AI: Calls navigate_to_page("heatmap")
    ↓
Backend: Emits WebSocket event { action: "navigate", payload: { path: "/monitoring/heatmap" } }
    ↓
Frontend AIContext: Receives event, calls navigate("/monitoring/heatmap")
    ↓
React Router: Renders Heatmap page
```

### Example 2: Element Interaction

```
User: "filter reports to show only failed tests"
    ↓
AI: navigate_to_page("reports")
    ↓
AI: interact_with_element("reports-table", "filter", { status: "failed" })
    ↓
Frontend: Dispatches 'ai-interact' event
    ↓
ReportsTable component: useAIControllable receives event, applies filter
```

### Example 3: Guided Demo

```
User: "show me how to run a test"
    ↓
AI: navigate_to_page("run tests")
AI: highlight_element("host-selector", 3000)
AI: show_toast("First, select a host", "info")
    ↓
Frontend: Navigates, highlights dropdown, shows toast
```

---

## File Structure

```
frontend/src/
├── lib/
│   └── ai/
│       ├── index.ts              # Exports
│       └── pageSchema.ts         # Page element registry
├── hooks/
│   └── ai/
│       ├── index.ts              # Exports
│       └── useAIControllable.ts  # Component integration hook
├── contexts/
│   └── AIContext.tsx             # WebSocket event handling
│
backend_server/src/agent/
├── tools/
│   └── page_interaction.py       # UI control tools
├── core/
│   └── tool_bridge.py            # Tool registration
└── config.py                     # Tool list
```

---

## Adding New Controllable Elements

### Step 1: Add to Page Schema

```typescript
// frontend/src/lib/ai/pageSchema.ts
'/my-page': {
  path: '/my-page',
  name: 'My Page',
  description: 'Does something',
  elements: [
    { id: 'my-button', type: 'button', label: 'My Button', actions: ['click'] },
  ]
}
```

### Step 2: Add Hook to Component

```tsx
// MyPage.tsx
const MyPage = () => {
  const btnRef = useRef(null);
  
  useAIControllable({
    elementId: 'my-button',
    ref: btnRef,
    onAction: (action) => {
      if (action === 'click') doSomething();
    }
  });
  
  return <button ref={btnRef}>Click Me</button>;
};
```

### Step 3: (Optional) Add Backend Alias

```python
# backend_server/src/agent/tools/page_interaction.py
NAVIGATION_ALIASES = {
    # ...
    'my page': '/my-page',
}
```

---

## Troubleshooting

### AI says "Cannot navigate to X"

The page name isn't recognized. Check:
1. Is the alias in `NAVIGATION_ALIASES`?
2. Is the path in `PAGE_SCHEMAS`?

### Element doesn't respond to AI

1. Is `useAIControllable` added to the component?
2. Does the `elementId` match the schema?
3. Check browser console for `ai-interact` events

### No WebSocket events received

1. Check AIContext is connected (green indicator)
2. Check backend logs for `🟢 Broadcasting 'ui_action'`
3. Verify socket namespace is `/agent`

---

## Security Considerations

- **Read-only by default**: AI can navigate but can't submit forms without explicit action handlers
- **No direct DOM access**: AI works through registered elements only
- **User can override**: All AI actions are visible in the Agent Pilot panel
- **Session-scoped**: WebSocket events only go to the user's session

---

## Future Enhancements

- [ ] Element screenshot capture for AI vision
- [ ] Record user actions → AI learns new interactions
- [ ] Multi-step macros (AI saves and replays workflows)
- [ ] Voice commands integration

