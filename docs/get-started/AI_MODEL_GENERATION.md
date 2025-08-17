# AI Model Generation - How It Works

## Overview

AI Model Generation automatically explores user interfaces and creates complete navigation trees with nodes and edges. The AI analyzes screenshots, tests navigation, and builds the navigation structure step-by-step.

## Quick Start

### 1. Prerequisites
- Device connected and controlled in NavigationEditor
- Take device control (button must be active)
- Ensure you're on the home screen of your interface

### 2. Starting AI Generation
1. Open NavigationEditor for your tree (e.g., `horizon_android_mobile`)
2. Take device control using the control panel
3. **AI Generate** button appears in the header (only when control is active)
4. Click **AI Generate** to open the exploration modal

### 3. Configuration
- **Exploration Depth**: Set how deep to explore (1-10 levels, default: 5)
- **Tree Info**: Shows current tree, host, and device
- Click **Start Exploration** to begin

### 4. Real-Time Monitoring
The modal shows live progress:
- **Current Step**: What the AI is currently doing
- **Progress**: Screens analyzed, nodes/edges found
- **AI Analysis**: What elements the AI sees on screen
- **AI Reasoning**: Why the AI is making specific decisions

### 5. Review & Approve
When exploration completes:
- **Proposed Nodes**: List of screens discovered with checkboxes
- **Proposed Edges**: Navigation paths found with checkboxes
- **User Decision**: Select which items to create
- Click **Generate** to create selected items in database

## How It Works Technically

### Step 1: Screenshot Analysis
```
AI takes screenshot → OpenRouter AI analyzes image → Identifies interactive elements
```

### Step 2: Navigation Testing
```
Test DPAD_RIGHT → Screenshot → AI analysis → Create node/edge if new screen found
Test DPAD_DOWN → Screenshot → AI analysis → Create node/edge if new screen found
Test DPAD_LEFT → Screenshot → AI analysis → Create node/edge if new screen found
Test DPAD_UP → Screenshot → AI analysis → Create node/edge if new screen found
```

### Step 3: Node & Edge Creation
- **Nodes**: Created for each unique screen discovered
- **Edges**: Created for successful navigation paths
- **Naming**: Follows existing convention (`home`, `home_dpad_right`, etc.)

### Step 4: Database Integration
- Uses existing `navigation_trees`, `navigation_nodes`, `navigation_edges` tables
- Same data structure as manually created navigation
- Integrates seamlessly with existing ReactFlow visualization

## Technical Architecture

### Frontend Components
- **AIGenerationModal**: Real-time exploration interface
- **useGenerateModel Hook**: Manages exploration state and polling
- **5-Second Polling**: Updates progress every 5 seconds during exploration

### Backend Infrastructure
- **Server Routes**: `/server/ai-generation/*` - Handle client requests
- **Host Routes**: `/host/ai-generation/*` - Execute actual exploration
- **Existing Controllers**: Reuses `AndroidMobileController`, `VideoAIHelpers`

### AI Analysis
- **OpenRouter Integration**: Uses existing Qwen vision model
- **Image Understanding**: Analyzes screenshots to identify UI elements
- **Decision Making**: Determines which navigation commands to test

## Exploration Strategy

### Sibling-First Approach
1. **Current Screen**: Analyze what's visible
2. **Test All Directions**: Try all navigation options (up/down/left/right)
3. **Document Results**: Create nodes/edges for successful navigation
4. **Progress Systematically**: Ensure complete coverage

### Navigation Commands
- **DPAD_RIGHT**: Test right navigation
- **DPAD_DOWN**: Test down navigation  
- **DPAD_LEFT**: Test left navigation
- **DPAD_UP**: Test up navigation
- **BACK**: Return to previous screen after testing

### Error Handling
- **Screenshot Failures**: Logged and reported
- **Navigation Failures**: Skipped, exploration continues
- **AI Analysis Failures**: Graceful degradation
- **User Cancellation**: Clean termination at any time

## Example Exploration Flow

```
1. User clicks "AI Generate" → Modal opens
2. User sets depth to 5 → Clicks "Start Exploration"
3. AI takes screenshot of home screen
4. AI analyzes: "Found 4 menu items: Live, VOD, Settings, Guide"
5. AI tests DPAD_RIGHT → New screen detected → Creates "home_dpad_right" node
6. AI tests DPAD_DOWN → Same screen → No new node
7. AI tests DPAD_LEFT → New screen detected → Creates "home_dpad_left" node  
8. AI tests DPAD_UP → New screen detected → Creates "home_dpad_up" node
9. Exploration completes → Shows 4 proposed nodes, 3 proposed edges
10. User selects all → Clicks "Generate" → Items created in database
11. ReactFlow refreshes → New navigation structure visible
```

## Best Practices

### Before Starting
- ✅ Ensure device is on stable home screen
- ✅ Check device control is active and responsive
- ✅ Start with lower depth (3-5) for initial testing
- ✅ Ensure stable network connection

### During Exploration
- ✅ Monitor progress in real-time
- ✅ Watch for AI reasoning to understand decisions
- ✅ Can cancel at any time if needed
- ✅ Wait for completion before making changes

### After Completion
- ✅ Review all proposed nodes and edges carefully
- ✅ Uncheck any items that seem incorrect
- ✅ Generate only the items you want to keep
- ✅ Test the generated navigation manually

## Troubleshooting

### Common Issues

**"AI Generate button not visible"**
- Ensure device control is active (take control first)
- Check that host and device are properly connected

**"Exploration fails immediately"**
- Check device is responsive to commands
- Ensure screenshot capture is working
- Verify OpenRouter API access

**"No nodes/edges generated"**
- Try starting from a different screen
- Check that navigation commands work manually
- Increase exploration depth

**"Generated navigation doesn't work"**
- Review proposed edges before approving
- Test navigation manually before generating
- Check device model compatibility

### Debug Information
- All exploration steps are logged to console
- AI analysis responses are captured
- Navigation command results are tracked
- Screenshot paths are preserved for review

## Integration with Existing Features

### NavigationEditor
- **Seamless Integration**: Works within existing editor
- **Same UI Patterns**: Follows established modal patterns
- **Control Dependency**: Respects existing control states

### Navigation Trees
- **Same Database**: Uses existing tables and schema
- **Compatible Format**: Generated nodes/edges work with all features
- **ReactFlow Integration**: Immediately visible in navigation view

### Device Control
- **Existing Controllers**: Uses same remote control infrastructure
- **Screenshot System**: Leverages existing capture mechanisms
- **Command Execution**: Uses established command patterns

This AI Model Generation feature provides a powerful way to rapidly create navigation structures while maintaining full compatibility with your existing navigation system.
