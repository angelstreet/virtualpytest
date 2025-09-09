# Grafana Alert Configuration for Incident Management

## Overview

This document provides the exact configuration needed to set up Grafana alerts for our new incident management system. The alerts are designed to provide proactive notifications for critical system issues.

## Prerequisites

✅ **Dashboard Updated**: System Monitoring dashboard now includes alerting stat panels  
✅ **Database Views Created**: `active_incidents_summary` and `device_availability_summary` views are available  
✅ **Contact Points**: Email receiver contact point is configured  

## Alert Rules to Configure

### 1. 🚨 Critical Incidents Alert

**Purpose**: Immediately notify when critical incidents are detected

**Configuration**:
- **Rule Name**: `Critical Incidents Detected`
- **Datasource**: `Local Metrics (PostgreSQL)`
- **Query**: 
```sql
SELECT critical_incidents FROM active_incidents_summary
```
- **Condition**: `IS ABOVE 0`
- **Evaluation**: Every `1m` for `1m`
- **Severity**: `Critical`
- **Summary**: `🚨 CRITICAL: {{ $values.A.Value }} critical incidents detected - immediate attention required`
- **Description**: `Critical incidents have been detected in the system. Check the Active Incidents panel in Grafana for details.`
- **Contact Point**: `email receiver`

### 2. 📉 Low Device Availability Alert

**Purpose**: Alert when device availability drops below acceptable levels

**Configuration**:
- **Rule Name**: `Low Device Availability`
- **Datasource**: `Local Metrics (PostgreSQL)`
- **Query**:
```sql
SELECT COUNT(*) as low_availability_count FROM device_availability_summary WHERE is_low_availability = 1
```
- **Condition**: `IS ABOVE 0`
- **Evaluation**: Every `5m` for `5m`
- **Severity**: `Warning`
- **Summary**: `📉 AVAILABILITY: {{ $values.A.Value }} devices below 90% availability in last hour`
- **Description**: `One or more devices have availability below 90% in the last hour. Check Device Availability panel for details.`
- **Contact Point**: `email receiver`

### 3. 📊 High Active Incident Count Alert

**Purpose**: Alert when too many incidents are active simultaneously

**Configuration**:
- **Rule Name**: `High Active Incident Count`
- **Datasource**: `Local Metrics (PostgreSQL)`
- **Query**:
```sql
SELECT active_incidents FROM active_incidents_summary
```
- **Condition**: `IS ABOVE 10`
- **Evaluation**: Every `2m` for `2m`
- **Severity**: `Warning`
- **Summary**: `📊 HIGH LOAD: {{ $values.A.Value }} active incidents - system under stress`
- **Description**: `High number of active incidents detected. This may indicate systemic issues requiring investigation.`
- **Contact Point**: `email receiver`

### 4. ⚡ New Incidents Spike Alert

**Purpose**: Alert when many new incidents are created in a short time

**Configuration**:
- **Rule Name**: `New Incidents Spike`
- **Datasource**: `Local Metrics (PostgreSQL)`
- **Query**:
```sql
SELECT new_incidents_5min FROM active_incidents_summary
```
- **Condition**: `IS ABOVE 5`
- **Evaluation**: Every `1m` for `2m`
- **Severity**: `Warning`
- **Summary**: `⚡ SPIKE: {{ $values.A.Value }} new incidents in last 5 minutes`
- **Description**: `Unusual spike in new incidents detected. This may indicate a cascading failure or system-wide issue.`
- **Contact Point**: `email receiver`

## Manual Setup Instructions

### Step 1: Access Grafana Alerting
1. Go to your Grafana instance
2. Navigate to **Alerting** → **Alert Rules**
3. Click **New Rule**

### Step 2: Configure Each Alert Rule
For each alert above:

1. **Set Query**:
   - Select datasource: `Local Metrics`
   - Enter the SQL query from above
   - Set RefID to `A`

2. **Set Condition**:
   - Add condition: `IS ABOVE [threshold]`
   - Use the threshold specified for each alert

3. **Set Evaluation**:
   - Evaluation group: Create new group `incident-monitoring`
   - Evaluation interval: As specified per alert
   - Pending period: As specified per alert

4. **Add Labels**:
   - `severity`: `critical` or `warning`
   - `team`: `infrastructure`
   - `system`: `monitoring`

5. **Add Annotations**:
   - `summary`: Use the summary template from above
   - `description`: Use the description from above
   - `runbook_url`: `https://your-docs/incident-response`

6. **Configure Notifications**:
   - Contact point: `email receiver`
   - Continue on error: `false`

### Step 3: Test Alerts
1. **Trigger Test**: Use **Test** button in alert rule configuration
2. **Verify Queries**: Ensure queries return expected values
3. **Check Notifications**: Verify email notifications are received

## Alert Notification Templates

### Email Template Enhancement
Configure your email contact point with this enhanced template:

**Subject**: `[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}`

**Body**:
```
🚨 INCIDENT MANAGEMENT ALERT

Status: {{ .Status | toUpper }}
Severity: {{ .GroupLabels.severity | toUpper }}
Time: {{ .StartsAt.Format "2006-01-02 15:04:05" }}

{{ range .Alerts }}
Alert: {{ .Annotations.summary }}
Details: {{ .Annotations.description }}

Dashboard: http://your-grafana/d/system-monitoring/system-monitoring
{{ end }}

---
Automated alert from Incident Management System
```

## Alert Silencing Rules

### Maintenance Windows
Create silencing rules for planned maintenance:

1. **Maintenance Silence**:
   - **Matchers**: `system=monitoring`
   - **Duration**: `2h` (adjust as needed)
   - **Comment**: `Planned maintenance window`

### Known Issues
Create silences for known issues being worked on:

1. **Known Issue Silence**:
   - **Matchers**: `alertname=Critical Incidents Detected`
   - **Duration**: `1h`
   - **Comment**: `Known issue - team working on resolution`

## Monitoring Alert Health

### Alert Rule Health Checks
Monitor your alert rules with these queries:

```sql
-- Check if alert views are working
SELECT * FROM active_incidents_summary;
SELECT * FROM device_availability_summary LIMIT 5;

-- Verify recent incident data
SELECT COUNT(*) as recent_incidents 
FROM system_incident 
WHERE detected_at >= NOW() - INTERVAL '1 hour';
```

### Alert Performance Metrics
Track alert effectiveness:
- **Alert Frequency**: How often alerts fire
- **False Positive Rate**: Alerts that don't require action
- **Response Time**: Time from alert to acknowledgment
- **Resolution Time**: Time from alert to incident resolution

## Integration with External Systems

### Slack Integration (Optional)
If you want to add Slack notifications:

1. Create Slack contact point
2. Use webhook URL from Slack app
3. Configure message template:
```json
{
  "text": "🚨 {{ .GroupLabels.alertname }}",
  "attachments": [
    {
      "color": "{{ if eq .Status \"firing\" }}danger{{ else }}good{{ end }}",
      "title": "{{ .GroupLabels.alertname }}",
      "text": "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}",
      "footer": "Grafana Alert"
    }
  ]
}
```

### PagerDuty Integration (Optional)
For critical incident escalation:

1. Create PagerDuty contact point
2. Use integration key from PagerDuty service
3. Configure for `Critical` severity alerts only

## Troubleshooting

### Common Issues

1. **Alerts Not Firing**:
   - Check datasource connectivity
   - Verify query syntax in Query Inspector
   - Ensure evaluation interval is appropriate

2. **False Positives**:
   - Adjust thresholds based on baseline metrics
   - Increase evaluation period for stability
   - Add additional conditions to reduce noise

3. **Missing Notifications**:
   - Verify contact point configuration
   - Check email server settings
   - Test contact point manually

### Query Debugging
Use these queries to debug alert issues:

```sql
-- Check current alert trigger values
SELECT 
    critical_incidents,
    active_incidents,
    new_incidents_5min
FROM active_incidents_summary;

-- Check device availability issues
SELECT 
    device_name,
    availability_percent,
    is_low_availability
FROM device_availability_summary 
WHERE is_low_availability = 1;
```

## Success Metrics

After implementing these alerts, you should achieve:

- **< 5 minute** detection time for critical incidents
- **< 1 minute** notification time for critical alerts
- **< 10%** false positive rate
- **> 95%** alert delivery success rate

This alert configuration transforms your monitoring from reactive to proactive, ensuring immediate awareness of system issues and enabling rapid incident response.
