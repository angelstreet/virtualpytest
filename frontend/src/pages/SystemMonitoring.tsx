import { Box } from '@mui/material';
import React from 'react';

const SystemMonitoring: React.FC = () => {
  // Get Grafana base URL from environment or use default
  const grafanaBaseUrl = (import.meta as any).env?.VITE_GRAFANA_URL || 'https://dev.virtualpytest.com/grafana';

  return (
    <Box
      sx={{
        width: '100%',
        height: '100vh',
        overflow: 'hidden',
      }}
    >
      <iframe
        src={`${grafanaBaseUrl}/d/system-monitoring/system-monitoring?orgId=1&refresh=30s&theme=light&kiosk`}
        width="100%"
        height="100%"
        frameBorder="0"
        title="System Monitoring"
        style={{
          border: 'none',
          display: 'block',
        }}
      />
    </Box>
  );
};

export default SystemMonitoring;
