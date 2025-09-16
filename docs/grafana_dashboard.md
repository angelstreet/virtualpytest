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

### 2. Device Alerts
- Purpose: Real-time device incident monitoring and alert management
- UID: device-alerts-dashboard
- Features: Active alerts tracking, incident analysis by device, blackscreen/freeze/audio monitoring, resolution metrics
- Key Panels: Alert counts, device-specific incident analysis, active incidents table, time series trends

### 3. System Server Monitoring
- Purpose: Comprehensive server performance and stability monitoring
- UID: system-monitoring
- Features: CPU, memory, disk usage, uptime tracking, availability metrics, reboot detection, CPU temperature monitoring
- Key Panels: Server status alerts, resource usage charts, availability calculations, reboot count and timeline, CPU temperature monitoring

### 4. Host Monitoring
- Purpose: System performance monitoring for host servers
- UID: fe85e054-7760-4133-8118-3dfe663dee66
- Features: CPU, memory, disk usage, uptime tracking, availability metrics, multi-host reboot analysis, CPU temperature comparison
- Key Panels: Host status overview, resource usage by host, availability charts, reboot monitoring by host, temperature monitoring

### 5. FullZap Results  
- Purpose: FullZap test campaign results
- UID: f0fa93e1-e6a3-4a46-a374-6666a925952c

### 6. Navigation Execution
- Purpose: Navigation execution performance monitoring
- UID: 467e4e29-d56b-44d9-b3e5-6e2fac687718

### 7. Navigation Metrics
- Purpose: Navigation metrics with nodes and edges
- UID: 9369e579-7f7a-47ec-ae06-f3a49e530b4f

## Navigation
- Route: /grafana-dashboard
- Location: After Test Results in main navigation

## New Monitoring Features

### 🔄 Reboot Detection
Advanced reboot monitoring across all dashboards using uptime analysis:
- **Smart Detection**: Identifies actual reboot events by analyzing uptime drops >1 hour
- **Duplicate Filtering**: 10-minute gap requirement prevents false positives
- **Time Range Aware**: Counts adjust based on selected time period
- **Multi-Host Support**: Tracks reboots per host independently

#### Server Dashboard Panels:
- **Reboots (Selected Period)**: Single stat showing total reboot count
- **Reboot Events Timeline**: Time series with red points marking reboot moments

#### Host Dashboard Panels:
- **Reboots by Host**: Vertical bar chart comparing reboot frequency across hosts
- **Host Reboot Events Timeline**: Multi-host timeline with color-coded reboot events

### 🌡️ CPU Temperature Monitoring
Real-time and historical CPU temperature tracking with thermal thresholds:
- **Temperature Thresholds**: Green (0-59°C), Yellow (60-74°C), Orange (75-84°C), Red (85°C+)
- **Null Handling**: Filters records where temperature data is available
- **Latest Values**: Shows most recent temperature readings per host

#### Server Dashboard Panels:
- **Server CPU Temp**: Single stat with current server temperature
- **Server CPU Temperature**: Time series showing temperature trends

#### Host Dashboard Panels:
- **Host CPU Temperature**: Vertical bar chart comparing temperatures across hosts
- **Host CPU Temperature Timeline**: Multi-host temperature trends over time

## Technical Details

### URL Format
{grafanaBaseUrl}/d/{slug}/{slug}?orgId=1&refresh=30s&theme=light&kiosk

## Dashboard URLs

### Direct Access Links:
- **System Server Monitoring**: `/grafana/d/system-monitoring/system-server-monitoring`
- **Host Monitoring**: `/grafana/d/fe85e054-7760-4133-8118-3dfe663dee66/system-host-monitoring`
- **Device Alerts**: `/grafana/d/device-alerts-dashboard/device-alerts-dashboard`
- **Script Results**: `/grafana/d/2a3b060a-7820-4a6e-aa2a-adcbf5408bd3/script-results-dashboard`

## Usage
1. Navigate to Grafana Dashboard from main menu
2. Select dashboard from dropdown
3. View in embedded iframe
4. Switch dashboards as needed
5. Use time picker to adjust monitoring period for reboot and temperature analysis
