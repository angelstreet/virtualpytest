import { Box, FormControl, InputLabel, MenuItem, Select, SelectChangeEvent } from '@mui/material';
import React, { useState } from 'react';

interface Dashboard {
  title: string;
  uid: string;
  url: string;
}

const GrafanaDashboard: React.FC = () => {
  // Hardcoded dashboards (excluding System Monitoring to avoid duplication)
  const dashboards: Dashboard[] = [
    {
      title: 'Script Results',
      uid: '2a3b060a-7820-4a6e-aa2a-adcbf5408bd3',
      url: '/grafana/d/2a3b060a-7820-4a6e-aa2a-adcbf5408bd3/script-results'
    },
    {
      title: 'FullZap Results',
      uid: 'f0fa93e1-e6a3-4a46-a374-6666a925952c',
      url: '/grafana/d/f0fa93e1-e6a3-4a46-a374-6666a925952c/fullzap-results'
    },
    {
      title: 'Navigation Execution',
      uid: '467e4e29-d56b-44d9-b3e5-6e2fac687718',
      url: '/grafana/d/467e4e29-d56b-44d9-b3e5-6e2fac687718/navigation-execution'
    },
    {
      title: 'Navigation Metrics',
      uid: '9369e579-7f7a-47ec-ae06-f3a49e530b4f',
      url: '/grafana/d/9369e579-7f7a-47ec-ae06-f3a49e530b4f/navigation-metrics'
    }
  ];

  // Default to Script Results
  const [selectedDashboard, setSelectedDashboard] = useState<string>('2a3b060a-7820-4a6e-aa2a-adcbf5408bd3');

  // Get Grafana base URL from environment or use default
  const grafanaBaseUrl = (import.meta as any).env?.VITE_GRAFANA_URL || 'https://dev.virtualpytest.com/grafana';

  const handleDashboardChange = (event: SelectChangeEvent<string>) => {
    setSelectedDashboard(event.target.value);
  };

  const selectedDashboardData = dashboards.find(d => d.uid === selectedDashboard);

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Dashboard Selector */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
        <FormControl sx={{ minWidth: 300 }}>
          <InputLabel id="dashboard-select-label">Select Dashboard</InputLabel>
          <Select
            labelId="dashboard-select-label"
            id="dashboard-select"
            value={selectedDashboard}
            label="Select Dashboard"
            onChange={handleDashboardChange}
          >
            {dashboards.map((dashboard) => (
              <MenuItem key={dashboard.uid} value={dashboard.uid}>
                {dashboard.title}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Dashboard iframe */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        {selectedDashboardData && (
          <iframe
            src={`${grafanaBaseUrl}${selectedDashboardData.url}?orgId=1&refresh=30s&theme=light&kiosk`}
            width="100%"
            height="100%"
            frameBorder="0"
            title={selectedDashboardData.title}
            style={{
              border: 'none',
              display: 'block',
            }}
          />
        )}
      </Box>
    </Box>
  );
};

export default GrafanaDashboard;
