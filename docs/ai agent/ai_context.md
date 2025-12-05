# AI Context & Overlay Architecture

This document describes the architecture of the AI "Mission Control" Overlay system in VirtualPyTest.

## Overview

The AI Overlay is a global, omni-directional interface layer that sits on top of the entire application. It replaces the traditional "Chat Page" paradigm with a "Co-Pilot" paradigm where the AI assists the user in context, regardless of which page they are viewing.

## Core Components

### 1. AI Context (`frontend/src/contexts/AIContext.tsx`)

The `AIProvider` wraps the entire application (`App.tsx`) and manages the global state of the AI interface.

**State Managed:**
- `isCommandOpen`: Visibility of the central Command Bar (Cmd+K).
- `isPilotOpen`: Visibility of the Right Panel (Agent Status/Steps).
- `isLogsOpen`: Visibility of the Bottom Panel (Terminal Logs).
- `activeTask`: The current high-level goal (e.g., "Run smoke test on S21").
- `isProcessing`: Whether the agent is currently "thinking" or working.

**Key Actions:**
- `toggleCommand()`, `openCommand()`, `closeCommand()`
- `setTask(task: string)`
- `setProcessing(processing: boolean)`

### 2. Omni-Overlay (`frontend/src/components/ai/AIOmniOverlay.tsx`)

A transparent, click-through layer (`pointer-events: none`) fixed to the viewport (`z-index: 9999`). It contains the three sub-panels, which have `pointer-events: auto` to allow interaction.

### 3. Command Bar (`frontend/src/components/ai/AICommandBar.tsx`)

- **Trigger:** Press `Cmd+K` or click the floating "Ask AI Agent" pill at the bottom center.
- **Behavior:** 
  - Dims the background (Focus Mode).
  - Accepts natural language commands.
  - On submit: Sets the `activeTask`, opens the Right Panel, and triggers the AI processing flow.

### 4. Agent Pilot Panel (`frontend/src/components/ai/panels/AgentPilotPanel.tsx`)

- **Position:** Fixed Right Sidebar.
- **Purpose:** Displays the "Brain" of the agent.
- **Content:**
  - Current Mission Status (e.g., "Connecting to device...").
  - Step-by-step execution list.
  - Artifact cards (e.g., "Test Report Generated", "Bug Ticket Created").

### 5. Log Terminal Panel (`frontend/src/components/ai/panels/LogTerminalPanel.tsx`)

- **Position:** Fixed Bottom Panel.
- **Purpose:** The "Engineer's View".
- **Content:**
  - Real-time system logs.
  - WebSocket event stream.
  - Debugging output.

## Integration Flow

1. **User Interaction:**
   User presses `Cmd+K` and types "Go to device control and connect to Pixel 5".

2. **Context Update:**
   - `activeTask` = "Go to device control..."
   - `isProcessing` = true
   - `isPilotOpen` = true

3. **Agent Execution (Future Implementation):**
   - The `AIOrchestrator` (hook) listens to `activeTask` changes.
   - Takes control of React Router -> `navigate('/device-control')`.
   - Calls Device API -> `connectDevice('pixel-5')`.
   - Updates `AIContext` with progress steps.

## File Structure

```
frontend/src/
├── components/
│   └── ai/
│       ├── AIOmniOverlay.tsx       # Main Container
│       ├── AICommandBar.tsx        # Floating Input
│       └── panels/
│           ├── AgentPilotPanel.tsx # Right Sidebar
│           └── LogTerminalPanel.tsx # Bottom Terminal
├── contexts/
│   └── AIContext.tsx               # Global State
└── App.tsx                         # Integration Point
```

## Usage Guidelines

- **Do not** put heavy logic inside the UI components. Use custom hooks (`useAIOrchestrator`) to bridge the UI and the Backend.
- **Do** use the `useAIContext()` hook in any component that needs to trigger the AI or react to its state.
- **Do** ensure the overlay `pointer-events` logic remains correct so users can still interact with the main app while the AI is active (unless the specific panel blocks it).

