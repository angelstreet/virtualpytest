import {
  Visibility as MonitorIcon,
  Timeline as MetricsIcon,
  Speed as PerformanceIcon,
  Dashboard as DashboardIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Alert,
  Chip,
  LinearProgress,
  Button,
  Tabs,
  Tab,
} from '@mui/material';
import React, { useState } from 'react';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`monitoring-tabpanel-${index}`}
      aria-labelledby={`monitoring-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 0 }}>{children}</Box>}
    </div>
  );
}

const SystemMonitoring: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Get Grafana base URL from environment or use default
  const grafanaBaseUrl = process.env.REACT_APP_GRAFANA_URL || 'http://localhost:5109/grafana';

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          System Monitoring
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Real-time monitoring of system performance, FFmpeg processes, and capture monitoring.
        </Typography>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="monitoring tabs">
          <Tab 
            label="Overview" 
            icon={<MonitorIcon />} 
            iconPosition="start"
            id="monitoring-tab-0"
            aria-controls="monitoring-tabpanel-0"
          />
          <Tab 
            label="Grafana Dashboard" 
            icon={<DashboardIcon />} 
            iconPosition="start"
            id="monitoring-tab-1"
            aria-controls="monitoring-tabpanel-1"
          />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>

      <Grid container spacing={3}>
        {/* System Status */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <MonitorIcon color="primary" />
                <Typography variant="h6">System Status</Typography>
              </Box>
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Test Runner</Typography>
                  <Chip label="Idle" color="default" size="small" />
                </Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Device Pool</Typography>
                  <Chip label="Available" color="success" size="small" />
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">API Server</Typography>
                  <Chip label="Online" color="success" size="small" />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <PerformanceIcon color="secondary" />
                <Typography variant="h6">Performance</Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="body2" gutterBottom>
                  CPU Usage
                </Typography>
                <LinearProgress variant="determinate" value={25} sx={{ mb: 2 }} />
                <Typography variant="body2" gutterBottom>
                  Memory Usage
                </Typography>
                <LinearProgress variant="determinate" value={45} sx={{ mb: 2 }} />
                <Typography variant="body2" gutterBottom>
                  Network I/O
                </Typography>
                <LinearProgress variant="determinate" value={15} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Test Metrics */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <MetricsIcon color="info" />
                <Typography variant="h6">Test Metrics</Typography>
              </Box>
              <Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Tests Run Today</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    0
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Success Rate</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    N/A
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Avg Duration</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    N/A
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Live Test Feed */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Live Test Feed
              </Typography>
              <Typography variant="body2" color="textSecondary" mb={2}>
                Real-time updates from running tests and system events.
              </Typography>
              <Box
                sx={{
                  p: 3,
                  textAlign: 'center',
                  borderRadius: 1,
                  minHeight: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="body2" color="textSecondary">
                  No active tests to monitor
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                System Monitoring Dashboard
              </Typography>
              <Button
                variant="outlined"
                startIcon={<DashboardIcon />}
                onClick={() => window.open(`${grafanaBaseUrl}/d/system-monitoring/system-monitoring`, '_blank')}
                size="small"
              >
                Open in Grafana
              </Button>
            </Box>
            
            <Box
              sx={{
                width: '100%',
                height: '800px',
                border: '1px solid #e0e0e0',
                borderRadius: 1,
                overflow: 'hidden',
              }}
            >
              <iframe
                src={`${grafanaBaseUrl}/d-solo/system-monitoring/system-monitoring?orgId=1&refresh=30s&theme=light&kiosk=tv`}
                width="100%"
                height="100%"
                frameBorder="0"
                title="System Monitoring Dashboard"
                style={{
                  border: 'none',
                  display: 'block',
                }}
              />
            </Box>
            
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Dashboard Features:</strong>
              </Typography>
              <Typography variant="body2" component="ul" sx={{ mt: 1, mb: 0 }}>
                <li>Real-time CPU, Memory, and Disk usage monitoring</li>
                <li>FFmpeg process health and file creation status</li>
                <li>Capture monitor process status and JSON file generation</li>
                <li>System uptime and host status overview</li>
                <li>Historical trends and performance metrics</li>
              </Typography>
            </Alert>
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default SystemMonitoring;
