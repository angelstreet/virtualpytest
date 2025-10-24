# Grafana Dashboard Exports

This directory contains exported Grafana dashboards in JSON format that can be easily imported into any Grafana instance.

## Exported Dashboards

1. **All Zapping Events** - `all-zapping-events.json`
2. **Deployment Table** - `deployment-table.json`
3. **Device Alerts Dashboard** - `device-alerts-dashboard.json`
4. **Device Information (Get Info)** - `device-information-get-info.json`
5. **DNS Lookup Time** - `dns-lookup-time.json`
6. **FullZap Results** - `fullzap-results.json`
7. **KPI Measurement** - `kpi-measurement.json`
8. **Navigation Metrics** - `navigation-metrics.json`
9. **Script Results** - `script-results.json`
10. **SmartPing Network Quality** - `smartping-network-quality.json`
11. **System Host Monitoring** - `system-host-monitoring.json`
12. **System Server Monitoring** - `system-server-monitoring.json`

## How to Import

### Via Grafana UI:
1. Open Grafana
2. Go to Dashboards → New → Import
3. Click "Upload JSON file" or paste the JSON content
4. Select the target folder (optional)
5. Configure datasource UIDs if needed
6. Click "Import"

### Via API:
```bash
curl -X POST http://your-grafana-instance/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @dashboard-filename.json
```

### Important Notes:
- These exports include the `folderUid` for organizational structure
- Datasource UIDs (e.g., `ceunuuxwxvy80e`) might need to be updated to match your target Grafana instance
- The `overwrite` flag is set to `false` to prevent accidental overwrites during import
- All dashboards are exported with their current version and configuration

## Folder Structure:
- **SCRIPT** folder: All Zapping Events, Deployment Table, FullZap Results, KPI Measurement, Navigation Metrics, Script Results
- **MONITORING** folder: Device Alerts Dashboard
- **GW** folder: Device Information, DNS Lookup Time, SmartPing Network Quality
- **SYSTEM** folder: System Host Monitoring, System Server Monitoring

## Export Date:
Generated on: 2025-10-24

## Compatibility:
- Grafana Version: 12.1.1
- Schema Version: 41

