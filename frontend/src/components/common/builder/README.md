# Shared Builder Components

**Container-based architecture**: Each component is a CONTAINER with exact styling, accepting content as children/slots.

## Architecture Principle

```
Container (shared styling) + Content Slot (pluggable components)
```

Each builder (TestCase, Campaign, etc.) uses the SAME containers but plugs in different content.

## Components

### 1. BuilderPageLayout
Fixed page container positioning content below navigation and above footer.

### 2. BuilderHeaderContainer  
Header container with exact TestCaseBuilder styling, accepts content as children.

### 3. BuilderSidebarContainer
Collapsible sidebar container, accepts any content inside.

### 4. BuilderMainContainer
Main content area container (sidebar + canvas).

### 5. BuilderStatsBarContainer
Bottom stats bar container with exact styling.

### 6. BuilderCanvasControls
React Flow canvas controls and background with exact styling.

All styling matches TestCaseBuilder EXACTLY.
