# Script Results Dashboard

## Overview
The Script Results dashboard provides comprehensive KPI monitoring and analysis for test script executions across different user interfaces. It offers both global metrics and per-interface breakdowns to understand volume, success rates, confidence levels, and performance trends.

## Dashboard Structure

### Panel 1: Global Script Execution KPIs (Stat Panel)
**Purpose**: High-level overview of all script execution metrics

**Metrics Displayed**:
- **Total Tests**: Total number of script executions
- **Success Rate (%)**: Overall percentage of successful test runs
- **Total Time (min)**: Cumulative execution time across all tests
- **Avg Duration (s)**: Average execution time per test

**Key Insights**:
- Overall system health and testing activity
- Global success rate trends
- Resource utilization (total execution time)
- Performance baseline (average duration)

### Panel 2: Success Rate by User Interface (Bar Chart)
**Purpose**: Compare success rates across different user interfaces

**Metrics**:
- **X-axis**: User Interface names
- **Primary Y-axis**: Success Rate (%)
- **Secondary Y-axis**: Test Volume (count)

**Key Insights**:
- Which interfaces are most/least reliable
- Correlation between test volume and success rate
- Interface-specific quality issues
- Confidence level based on test volume

### Panel 3: Test Volume by User Interface (Stacked Bar Chart)
**Purpose**: Visualize testing activity distribution and success/failure breakdown

**Metrics**:
- **X-axis**: User Interface names
- **Y-axis**: Number of tests (stacked)
- **Green Stack**: Successful tests
- **Red Stack**: Failed tests

**Key Insights**:
- Testing coverage per interface
- Absolute success/failure counts
- Interface testing priorities
- Resource allocation insights

### Panel 4: Execution Time Distribution by Interface (Bar Chart)
**Purpose**: Analyze performance characteristics and consistency

**Metrics**:
- **X-axis**: User Interface names
- **Avg Duration (s)**: Average execution time (blue)
- **Min/Max Duration (s)**: Performance range
- **Std Dev (s)**: Performance consistency indicator (orange)

**Key Insights**:
- Performance comparison between interfaces
- Execution time consistency (lower std dev = more predictable)
- Performance bottlenecks identification
- SLA compliance monitoring

### Panel 5: Success Rate Trend Over Time (Time Series)
**Purpose**: Monitor success rate stability and trends over time

**Metrics**:
- **X-axis**: Time (daily grouping)
- **Y-axis**: Success Rate (%)
- **Lines**: One per user interface

**Key Insights**:
- Success rate stability over time
- Trend identification (improving/degrading)
- Interface-specific performance patterns
- Confidence in long-term reliability

### Panel 6: Details (Table)
**Purpose**: Detailed view of individual script executions

**Columns**:
- **script_name**: Name of executed script
- **userinterface_name**: Target interface
- **host_name**: Execution host
- **device_name**: Target device
- **success**: Execution result (true/false)
- **started_at**: Execution start time
- **completed_at**: Execution completion time
- **execution_time_ms**: Duration in milliseconds
- **html_report_r2_url**: Link to detailed report
- **error_msg**: Error details (if failed)

## Key Performance Indicators (KPIs)

### Global KPIs
1. **Total Tests Run**: Overall testing activity volume
2. **Overall Success Rate**: System-wide reliability metric
3. **Total Execution Time**: Resource utilization indicator
4. **Average Duration**: Performance baseline

### Per User Interface KPIs
1. **Success Rate per Interface**: Interface-specific reliability
2. **Test Volume per Interface**: Coverage and activity distribution
3. **Average Execution Time per Interface**: Performance comparison
4. **Success Rate Trend**: Stability and improvement tracking

### Confidence Indicators
1. **Test Volume**: Higher volume = higher confidence in metrics
2. **Standard Deviation**: Lower std dev = more consistent performance
3. **Trend Stability**: Consistent success rates over time
4. **Minimum Execution Threshold**: Panels filter for ≥3 executions

## Usage Guidelines

### For Test Managers
- **Monitor Global KPIs**: Track overall testing health
- **Compare Interface Performance**: Identify problematic interfaces
- **Resource Planning**: Use volume and time metrics for capacity planning
- **Quality Assurance**: Monitor success rate trends

### For Developers
- **Performance Analysis**: Use execution time distribution for optimization
- **Error Investigation**: Drill down from failed tests to detailed reports
- **Interface Comparison**: Identify performance differences between platforms
- **Trend Analysis**: Monitor impact of code changes over time

### For Operations
- **System Health**: Monitor overall success rates and volumes
- **Capacity Planning**: Use execution time metrics for resource allocation
- **SLA Monitoring**: Track performance against defined thresholds
- **Incident Response**: Identify failing interfaces quickly

## Filtering and Time Ranges

### Default Settings
- **Time Range**: Last 30 days
- **Minimum Executions**: 3+ per interface (for statistical significance)
- **Refresh Rate**: Manual (can be set to auto-refresh)

### Recommended Time Ranges
- **Daily Monitoring**: Last 24 hours
- **Weekly Reviews**: Last 7 days
- **Monthly Reports**: Last 30 days
- **Trend Analysis**: Last 90 days or more

## Troubleshooting

### No Data Showing
1. Check time range - ensure it covers periods with test executions
2. Verify database connectivity
3. Confirm script_results table has data
4. Check user permissions

### Low Confidence Metrics
1. Increase test volume per interface
2. Extend time range for more data points
3. Review minimum execution threshold (currently 3)

### Performance Issues
1. Consider shorter time ranges for large datasets
2. Optimize database queries if dashboard loads slowly
3. Use appropriate refresh intervals

## Technical Details

### Data Source
- **Database**: PostgreSQL
- **Table**: `script_results`
- **Key Fields**: script_name, userinterface_name, success, started_at, execution_time_ms

### Query Patterns
- **Aggregations**: COUNT, SUM, AVG, ROUND for KPI calculations
- **Grouping**: By userinterface_name for interface-specific metrics
- **Time Filtering**: Uses Grafana's $__timeFilter() macro
- **Statistical Functions**: STDDEV for consistency metrics

### Panel Types Used
- **Stat Panel**: For global KPIs display
- **Bar Chart**: For comparative metrics
- **Time Series**: For trend analysis
- **Table**: For detailed drill-down

## Related Dashboards
- [Navigation Metrics](./navigation_metrics_dashboard.md): Node and edge performance
- [System Monitoring](./system_monitoring_dashboard.md): Infrastructure metrics
- [Grafana Dashboard](./grafana_dashboard.md): Multi-dashboard access

## Maintenance

### Regular Tasks
1. **Monitor Data Quality**: Ensure consistent data ingestion
2. **Review Thresholds**: Adjust success rate thresholds as needed
3. **Update Time Ranges**: Modify default ranges based on usage patterns
4. **Performance Optimization**: Monitor query performance and optimize as needed

### Updates and Changes
- Dashboard version tracking in Grafana
- Change log maintained in dashboard description
- Backup dashboard configuration before major changes
