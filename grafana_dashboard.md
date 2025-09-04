# 📊 Grafana Dashboard Documentation

## Overview
This dashboard provides comprehensive monitoring of model execution performance, displaying success rates, execution volumes, and detailed execution results for both edges (actions) and nodes (verifications).

---

## 📈 Panel Configurations

### Panel 1: Overall Success Rate
**Type:** Stat Panel  
**Description:** Shows the overall success rate across all executions

```sql
SELECT 
  ROUND(
    (SUM(CASE WHEN success THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1
  ) as "Success Rate"
FROM execution_results
WHERE $__timeFilter(executed_at)
```

**Configuration:**
- Visualization: Stat
- Unit: Percent (0-100)
- Thresholds: 
  - Green: >90%
  - Yellow: 70-90%
  - Red: <70%
- Title: "Overall Success Rate"

---

### Panel 2: Edge & Node Success Rates
**Type:** Bar Gauge (Horizontal)  
**Description:** Displays separate success rates for edges (actions) and nodes (verifications)

```sql
SELECT 
  'Edges' as metric,
  ROUND(
    (SUM(CASE WHEN er.success THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1
  ) as "Success Rate"
FROM execution_results er
WHERE er.execution_type = 'action' 
  AND $__timeFilter(er.executed_at)

UNION ALL

SELECT 
  'Nodes' as metric,
  ROUND(
    (SUM(CASE WHEN er.success THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1
  ) as "Success Rate"
FROM execution_results er
WHERE er.execution_type = 'verification' 
  AND $__timeFilter(er.executed_at)
```

**Configuration:**
- Visualization: Bar Gauge (Horizontal)
- Unit: Percent (0-100)
- Field Override: Display name: `${__field.labels.metric} Success Rate`
- Thresholds:
  - Green: >85%
  - Yellow: 60-85%
  - Red: <60%
- Title: "Edge & Node Success Rates"
- Legend: Show
- Orientation: Horizontal

---

### Panel 3: Executions Over Time
**Type:** Time Series  
**Description:** Shows execution volume trends over time

```sql
SELECT 
  $__timeGroup(executed_at, '1h') as time,
  COUNT(*) as "Executions"
FROM execution_results
WHERE $__timeFilter(executed_at)
GROUP BY time
ORDER BY time
```

**Configuration:**
- Visualization: Time Series (Area fill)
- Unit: Short
- Color: Green gradient
- Title: "Execution Volume"
- Fill opacity: 0.3
- Line width: 2

---

### Panel 4: ModelReports Table
**Type:** Table  
**Description:** Detailed execution results with metrics, showing individual elements with their performance data

```sql
-- ModelReports.tsx equivalent query for Grafana (FIXED with node names)
WITH latest_executions AS (
  -- Get the latest execution for each element (grouped like in transformedResults)
  SELECT DISTINCT ON (
    CASE 
      WHEN er.execution_type = 'action' AND er.action_set_id IS NOT NULL THEN 
        er.edge_id || '#' || er.action_set_id
      WHEN er.execution_type = 'action' THEN 
        COALESCE(er.edge_id, 'unknown')
      ELSE 
        COALESCE(er.node_id, 'unknown')
    END
  )
    -- Element grouping key
    CASE 
      WHEN er.execution_type = 'action' AND er.action_set_id IS NOT NULL THEN 
        er.edge_id || '#' || er.action_set_id
      WHEN er.execution_type = 'action' THEN 
        COALESCE(er.edge_id, 'unknown')
      ELSE 
        COALESCE(er.node_id, 'unknown')
    END as element_key,
    
    -- Basic info
    er.execution_type,
    er.tree_id,
    er.node_id,
    er.edge_id,
    
    -- IDs for metrics lookup
    COALESCE(er.edge_id, er.node_id) as element_id,
    er.action_set_id,
    er.executed_at,
    sr.html_report_r2_url

  FROM execution_results er
  LEFT JOIN script_results sr ON er.script_result_id = sr.id
  WHERE $__timeFilter(er.executed_at)
  ORDER BY 
    CASE 
      WHEN er.execution_type = 'action' AND er.action_set_id IS NOT NULL THEN 
        er.edge_id || '#' || er.action_set_id
      WHEN er.execution_type = 'action' THEN 
        COALESCE(er.edge_id, 'unknown')
      ELSE 
        COALESCE(er.node_id, 'unknown')
    END,
    er.executed_at DESC
)

SELECT 
  -- Columns matching ModelReports.tsx table exactly
  CASE WHEN le.execution_type = 'action' THEN 'Edge' ELSE 'Node' END as "Type",
  
  -- Interface from tree mapping
  COALESCE(ui.name, 'Unknown') as "Interface", 
  
  -- FIXED: Element name with proper node names from navigation_nodes table
  CASE 
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL AND le.action_set_id LIKE '%_to_%' THEN
      REPLACE(SPLIT_PART(le.action_set_id, '_to_', 1), '_', ' ') || ' → ' || 
      REPLACE(SPLIT_PART(le.action_set_id, '_to_', 2), '_', ' ')
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL THEN
      REPLACE(le.action_set_id, '_', ' ')
    WHEN le.execution_type = 'action' THEN
      'Edge ' || SUBSTRING(le.edge_id, 1, 8)
    ELSE
      -- Use actual node label from navigation_nodes table
      COALESCE(nn.label, 'Node ' || SUBSTRING(COALESCE(le.node_id, 'unknown'), 1, 8))
  END as "Name",
  
  -- Action/Verification details column
  CASE 
    WHEN le.execution_type = 'action' THEN
      CASE 
        WHEN le.action_set_id LIKE '%home%' THEN 'press_key {key: HOME, wait_time: 1500}'
        WHEN le.action_set_id LIKE '%back%' THEN 'press_key {key: BACK, wait_time: 2000}'
        WHEN le.action_set_id LIKE '%up%' THEN 'press_key {key: UP, wait_time: 1000}'
        WHEN le.action_set_id LIKE '%down%' THEN 'press_key {key: DOWN, wait_time: 1000}'
        WHEN le.action_set_id LIKE '%ok%' OR le.action_set_id LIKE '%enter%' THEN 'press_key {key: OK, wait_time: 1500}'
        ELSE 'press_key {key: OK, wait_time: 1500}'
      END
    ELSE
      'waitForElementToAppear Type: adb element: ' || LOWER(REPLACE(COALESCE(nn.label, le.node_id), ' ', '_'))
  END as "Action/Verification",
  
  -- Success rate from metrics
  CASE 
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL THEN
      CASE WHEN COALESCE(em.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(em.success_rate * 100) || '%' END
    WHEN le.execution_type = 'action' THEN
      CASE WHEN COALESCE(em_legacy.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(em_legacy.success_rate * 100) || '%' END
    ELSE
      CASE WHEN COALESCE(nm.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(nm.success_rate * 100) || '%' END
  END as "Success",
  
  -- Volume from metrics
  CASE 
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL THEN
      COALESCE(em.total_executions, 0)
    WHEN le.execution_type = 'action' THEN
      COALESCE(em_legacy.total_executions, 0)
    ELSE
      COALESCE(nm.total_executions, 0)
  END as "Volume",
  
  -- Duration from metrics
  CASE 
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL THEN
      CASE WHEN em.avg_execution_time_ms IS NULL THEN 'N/A'
           WHEN em.avg_execution_time_ms < 1000 THEN ROUND(em.avg_execution_time_ms) || 'ms'
           WHEN em.avg_execution_time_ms < 60000 THEN ROUND(em.avg_execution_time_ms/1000, 1) || 's'
           ELSE FLOOR(em.avg_execution_time_ms/60000) || 'm ' || ROUND((em.avg_execution_time_ms % 60000)/1000, 1) || 's'
      END
    WHEN le.execution_type = 'action' THEN
      CASE WHEN em_legacy.avg_execution_time_ms IS NULL THEN 'N/A'
           WHEN em_legacy.avg_execution_time_ms < 1000 THEN ROUND(em_legacy.avg_execution_time_ms) || 'ms'
           WHEN em_legacy.avg_execution_time_ms < 60000 THEN ROUND(em_legacy.avg_execution_time_ms/1000, 1) || 's'
           ELSE FLOOR(em_legacy.avg_execution_time_ms/60000) || 'm ' || ROUND((em_legacy.avg_execution_time_ms % 60000)/1000, 1) || 's'
      END
    ELSE
      CASE WHEN nm.avg_execution_time_ms IS NULL THEN 'N/A'
           WHEN nm.avg_execution_time_ms < 1000 THEN ROUND(nm.avg_execution_time_ms) || 'ms'
           WHEN nm.avg_execution_time_ms < 60000 THEN ROUND(nm.avg_execution_time_ms/1000, 1) || 's'
           ELSE FLOOR(nm.avg_execution_time_ms/60000) || 'm ' || ROUND((nm.avg_execution_time_ms % 60000)/1000, 1) || 's'
      END
  END as "Duration",
  
  -- Confidence
  CASE 
    WHEN le.execution_type = 'action' AND le.action_set_id IS NOT NULL THEN
      CASE WHEN COALESCE(em.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(em.success_rate * 10) || '/10' END
    WHEN le.execution_type = 'action' THEN
      CASE WHEN COALESCE(em_legacy.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(em_legacy.success_rate * 10) || '/10' END
    ELSE
      CASE WHEN COALESCE(nm.total_executions, 0) = 0 THEN 'N/A'
           ELSE ROUND(nm.success_rate * 10) || '/10' END
  END as "Confidence",
  
  -- Executed date
  TO_CHAR(le.executed_at, 'DD/MM/YYYY, HH24:MI:SS') as "Executed",
  
  -- Report URL
  le.html_report_r2_url as "Report URL"

FROM latest_executions le
-- Join with navigation trees and user interfaces
LEFT JOIN navigation_trees nt ON le.tree_id = nt.id
LEFT JOIN userinterfaces ui ON nt.userinterface_id = ui.id
-- NEW: Join with navigation_nodes to get actual node labels/names
LEFT JOIN navigation_nodes nn ON (le.node_id = nn.node_id AND le.tree_id = nn.tree_id)
-- Join with edge metrics for direction-specific actions
LEFT JOIN edge_metrics em ON (
  le.execution_type = 'action' 
  AND le.action_set_id IS NOT NULL 
  AND em.edge_id = le.element_id 
  AND em.action_set_id = le.action_set_id
)
-- Join with edge metrics for legacy actions
LEFT JOIN edge_metrics em_legacy ON (
  le.execution_type = 'action' 
  AND le.action_set_id IS NULL 
  AND em_legacy.edge_id = le.element_id 
  AND em_legacy.action_set_id IS NULL
)
-- Join with node metrics for verifications
LEFT JOIN node_metrics nm ON (
  le.execution_type = 'verification' 
  AND nm.node_id = le.element_id
)

ORDER BY le.executed_at DESC
LIMIT 500
```

**Configuration:**
- Visualization: Table
- Title: "ModelReports - Detailed Execution Results"
- Columns:
  - **Type**: Element type (Edge/Node)
  - **Interface**: User interface name
  - **Name**: Readable element name (formatted action_set_id for edges, node labels for nodes)
  - **Action/Verification**: Command details
  - **Success**: Success rate percentage
  - **Volume**: Total execution count
  - **Duration**: Average execution time
  - **Confidence**: Confidence score (0-10)
  - **Executed**: Last execution timestamp
  - **Report URL**: Link to execution report

---

## 🎨 Dashboard Layout

```
┌──────────────┬──────────────────────┬───────────────────────┐
│   Overall    │  Edge & Node Success │   Executions Over     │
│ Success Rate │    (Bar Gauge)       │   Time (Time Series)  │
│   (Stat)     │                      │                       │
└──────────────┴──────────────────────┴───────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                ModelReports Table                           │
│              (Detailed Execution Results)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Key Features

### Data Sources
- **Primary**: `execution_results` table
- **Supporting**: `navigation_trees`, `userinterfaces`, `navigation_nodes`, `edge_metrics`, `node_metrics`, `script_results`

### Time Filtering
All panels use `$__timeFilter(executed_at)` for consistent time range filtering via Grafana's time picker.

### Bidirectional Edge Support
The table query properly handles bidirectional edges by:
- Grouping by `edge_id#action_set_id` for direction-specific metrics
- Formatting action names with `→` arrows (e.g., "home → live")
- Joining with appropriate metrics tables based on `action_set_id`

### Performance Optimizations
- Uses `DISTINCT ON` for efficient grouping
- Limits table results to 500 rows
- Indexes recommended on: `executed_at`, `execution_type`, `edge_id`, `node_id`, `action_set_id`

---

## 📋 Setup Instructions

1. **Create Dashboard**: Import or create new dashboard in Grafana
2. **Add Data Source**: Configure PostgreSQL connection to your Supabase database
3. **Add Panels**: Create 4 panels using the queries above
4. **Configure Layout**: Arrange panels as shown in the layout diagram
5. **Set Time Range**: Configure default time range (e.g., Last 24 hours)
6. **Save Dashboard**: Save with appropriate name and tags

---

## 🔍 Troubleshooting

### No Data Showing
1. Check time range - ensure it covers periods with execution data
2. Verify database connection and permissions
3. Test with simple query: `SELECT COUNT(*) FROM execution_results`

### Performance Issues
1. Add database indexes on frequently queried columns
2. Reduce time range for large datasets
3. Consider using materialized views for complex aggregations

### Missing Node Names
- Ensure `navigation_nodes` table is populated with proper labels
- Check that `node_id` and `tree_id` relationships are correct

---

## 📊 Metrics Explained

- **Success Rate**: Percentage of successful executions
- **Volume**: Total number of executions
- **Duration**: Average execution time (formatted as ms/s/m)
- **Confidence**: Success rate converted to 0-10 scale
- **Type**: Edge (action) or Node (verification)
- **Interface**: User interface name from navigation trees
- **Action/Verification**: Simplified command representation

---

## 🔄 Updates and Maintenance

- **Regular Review**: Monitor dashboard performance and adjust queries as needed
- **Index Maintenance**: Ensure database indexes are optimized for query patterns
- **Data Retention**: Consider archiving old execution results to maintain performance
- **Query Optimization**: Review and optimize queries based on usage patterns
