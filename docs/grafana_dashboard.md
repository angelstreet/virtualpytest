# Grafana Dashboard Page

## Overview
The Grafana Dashboard page provides a centralized interface for viewing all available Grafana dashboards. Users can select from a dropdown menu and view dashboards in an embedded iframe.

## Features
- Dashboard selection dropdown
- Full-screen iframe display
- 30-second auto-refresh
- Kiosk mode viewing

## Available Dashboards

### 1. Script Results (Default)
- Purpose: Comprehensive KPI monitoring for test script executions
- UID: 2a3b060a-7820-4a6e-aa2a-adcbf5408bd3
- Features: Global KPIs, success rates by interface, volume analysis, performance trends
- Documentation: [Script Results Dashboard Guide](./script_results_dashboard.md)

### 2. FullZap Results  
- Purpose: FullZap test campaign results
- UID: f0fa93e1-e6a3-4a46-a374-6666a925952c

### 3. Navigation Execution
- Purpose: Navigation execution performance monitoring
- UID: 467e4e29-d56b-44d9-b3e5-6e2fac687718

### 4. Navigation Metrics
- Purpose: Navigation metrics with nodes and edges
- UID: 9369e579-7f7a-47ec-ae06-f3a49e530b4f

## Navigation
- Route: /grafana-dashboard
- Location: After Test Results in main navigation

## Technical Details

### URL Format
{grafanaBaseUrl}/d/{slug}/{slug}?orgId=1&refresh=30s&theme=light&kiosk

## Usage
1. Navigate to Grafana Dashboard from main menu
2. Select dashboard from dropdown
3. View in embedded iframe
4. Switch dashboards as needed
