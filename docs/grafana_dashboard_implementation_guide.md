# Grafana Dashboard Panel Grouping Implementation Guide

## Overview
This guide explains how to implement the grouped panel layout for your System Server Monitoring dashboard. The new layout organizes panels into logical groups, making it much easier to navigate when you have a limited number of servers.

## What's Been Created

### 1. Grouping Strategy Document
- **File**: `docs/grafana_dashboard_grouping_strategy.md`
- **Purpose**: Detailed explanation of the grouping logic and benefits

### 2. Grouped Dashboard Configuration
- **File**: `config/grafana/dashboards/system-monitoring-grouped.json`
- **Purpose**: Complete Grafana dashboard JSON with grouped panels

## New Dashboard Structure

### 🖥️ Server Health Overview (Row 1)
Quick status indicators for immediate server health assessment:
- **Server Status**: Online/Offline indicator with green/red color coding
- **CPU Temperature**: Current temperature with threshold-based coloring (Green <60°C, Yellow 60-80°C, Red >80°C)
- **Current Uptime**: How long the server has been running
- **Last Reboot**: When the server was last rebooted

### 📊 Availability Metrics (Row 2)
Server availability percentages across different time periods:
- **Daily Availability**: 24-hour availability percentage
- **Weekly Availability**: 7-day availability percentage  
- **Monthly Availability**: 30-day availability percentage
- **Yearly Availability**: 365-day availability percentage

**Color Coding**: Red (<90%), Yellow (90-95%), Green (>95%)

### ⏱️ Uptime & Downtime Analysis (Row 3)
Detailed breakdown of uptime and downtime periods:
- **Daily Uptime**: Hours of uptime in the last 24 hours
- **Weekly Downtime**: Days of downtime in the last 7 days
- **Monthly Downtime**: Days of downtime in the last 30 days
- **Yearly Downtime**: Days of downtime in the last 365 days

### 🌡️ Temperature Monitoring (Row 4)
Server thermal monitoring with time series visualization:
- **Server CPU Temperature**: Time series chart showing temperature trends
- Supports multiple server temperature sources (RPI1, RPI4, etc.)
- Color-coded lines for different servers

### 🔧 Debug & Detailed Metrics (Row 5 - Collapsible)
Technical details and troubleshooting information:
- **Server Availability Debug Data**: Detailed table with ping counts, expected vs received metrics
- Collapsed by default to reduce visual clutter
- Expandable when detailed analysis is needed

## Key Improvements

### 1. Visual Organization
- **Row Headers**: Clear section titles with emoji icons for easy identification
- **Consistent Spacing**: Uniform panel heights within each group
- **Logical Flow**: Information flows from high-level status to detailed analysis

### 2. Color Consistency
- **Availability Panels**: Consistent red/yellow/green thresholds across all time periods
- **Temperature Panels**: Heat-based color coding (green/yellow/red)
- **Status Panels**: Binary green/red for online/offline states

### 3. Space Efficiency
- **4-Panel Rows**: Optimal use of horizontal space
- **Collapsible Sections**: Debug information hidden by default
- **Appropriate Sizing**: Panels sized based on information density

### 4. Enhanced Readability
- **Clear Titles**: Descriptive panel titles with time periods
- **Appropriate Units**: Proper units for each metric (%, °C, days, hours)
- **Threshold Indicators**: Visual cues for normal/warning/critical states

## Implementation Steps

### Step 1: Backup Current Dashboard
Before implementing the grouped version, export your current dashboard:

1. Go to your Grafana instance
2. Navigate to the System Server Monitoring dashboard
3. Click the share icon → Export → Save to file
4. Keep this as a backup

### Step 2: Import Grouped Dashboard
1. In Grafana, go to Dashboards → Import
2. Upload the `config/grafana/dashboards/system-monitoring-grouped.json` file
3. Configure the data source (should be your PostgreSQL/Supabase connection)
4. Save the dashboard

### Step 3: Verify Data Sources
Ensure the dashboard queries work with your database:
- Check that `system_metrics` table exists
- Verify `host_name = 'server'` matches your server naming
- Test that temperature data (`cpu_temp` field) is available

### Step 4: Customize for Your Environment
Adjust the dashboard for your specific setup:

#### Server Names
If your server has a different name than 'server', update the queries:
```sql
-- Change this:
WHERE host_name = 'server'
-- To this:
WHERE host_name = 'your-server-name'
```

#### Temperature Sources
If you have different temperature sensors, update the temperature panel:
```sql
-- Add your temperature sources:
SELECT 
  timestamp as time,
  cpu_temp as "YourServer-cpu_temp"
FROM system_metrics 
WHERE host_name = 'your-server-name'
```

#### Thresholds
Adjust color thresholds based on your requirements:
- **Availability**: Currently set to Red (<90%), Yellow (90-95%), Green (>95%)
- **Temperature**: Currently set to Green (<60°C), Yellow (60-80°C), Red (>80°C)

### Step 5: Test the Dashboard
1. **Verify Data**: Check that all panels show data
2. **Test Thresholds**: Confirm color coding works correctly
3. **Check Responsiveness**: Test on different screen sizes
4. **Validate Queries**: Ensure all SQL queries execute without errors

## Troubleshooting

### Common Issues

#### 1. No Data Showing
- **Check Data Source**: Verify PostgreSQL connection is working
- **Verify Table Names**: Ensure `system_metrics` table exists
- **Check Time Range**: Make sure you have data in the selected time range

#### 2. Wrong Colors
- **Review Thresholds**: Check threshold values in panel settings
- **Verify Data Types**: Ensure numeric fields are properly formatted

#### 3. Layout Issues
- **Grid Positions**: Verify panel grid positions don't overlap
- **Panel Heights**: Adjust heights if panels appear cramped

#### 4. Query Errors
- **SQL Syntax**: Check for PostgreSQL-specific syntax
- **Field Names**: Verify field names match your database schema
- **Time Filters**: Ensure `$__timeFilter` macro is supported

## Benefits of the Grouped Layout

### For Small Server Environments
- **Reduced Clutter**: Related metrics are visually grouped
- **Easier Navigation**: Clear sections make finding information faster
- **Better Overview**: High-level status is immediately visible
- **Scalable Design**: Can easily add more servers to existing groups

### For Monitoring Teams
- **Faster Troubleshooting**: Debug information is organized but not overwhelming
- **Clear Priorities**: Critical information is prominently displayed
- **Consistent Experience**: Similar layouts across different dashboards

### For Management
- **Executive Summary**: Top rows provide high-level health status
- **Trend Analysis**: Availability metrics show performance over time
- **Resource Planning**: Temperature and uptime data inform capacity decisions

## Next Steps

1. **Test the Implementation**: Import and verify the grouped dashboard works
2. **Gather Feedback**: Get input from dashboard users on the new layout
3. **Iterate**: Refine groupings based on actual usage patterns
4. **Document**: Update team documentation with the new dashboard structure
5. **Extend**: Apply similar grouping to other monitoring dashboards

The grouped dashboard layout will significantly improve your monitoring experience, especially with a limited number of servers. The logical organization makes it much easier to quickly assess server health and dive into specific metrics when needed.
