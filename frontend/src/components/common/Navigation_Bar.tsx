import {
  Science as TestIcon,
  Campaign as CampaignIcon,
  PlayArrow as RunIcon,
  Visibility as MonitorIcon,
  Assessment as ReportsIcon,
  Devices as DevicesIcon,
  AccountTree as TreeIcon,
  Settings as SettingsIcon,
  Storage as CollectionIcon,
  Gamepad as ControllerIcon,
  LibraryBooks as LibraryIcon,
  Memory as ModelIcon,
  BugReport as TestingIcon,
  Link as LinkIcon,
  Warning as IncidentIcon,
  GridView as HeatmapIcon,
  Notifications as NotificationsIcon,
  Dashboard as DashboardIcon,
  SmartToy as AIIcon,
  Api as ApiIcon,
  Build as BuildIcon, // NEW: For Builder section
} from '@mui/icons-material';
import { Box, Button } from '@mui/material';
import React from 'react';
import { Link, useLocation } from 'react-router-dom';

import NavigationDropdown from './Navigation_Dropdown';
import NavigationGroupedDropdown from './Navigation_GroupedDropdown';

const NavigationBar: React.FC = () => {
  const location = useLocation();

  // Navigation menu configuration
  const testGroups = [
    {
      sectionLabel: 'Builder',
      items: [
        { label: 'Test Builder', path: '/builder/test-builder', icon: <TreeIcon fontSize="small" /> },
        { label: 'Campaign Builder', path: '/builder/campaign-builder', icon: <BuildIcon fontSize="small" /> },
      ],
    },
    {
      sectionLabel: 'Test Plan',
      items: [
        { label: 'Test Cases', path: '/test-plan/test-cases', icon: <TestIcon fontSize="small" /> },
        { label: 'Campaigns', path: '/test-plan/campaigns', icon: <CampaignIcon fontSize="small" /> },
        {
          label: 'Collections',
          path: '/test-plan/collections',
          icon: <CollectionIcon fontSize="small" />,
        },
      ],
    },
    {
      sectionLabel: 'Execution',
      items: [
        { label: 'Run Tests', path: '/test-execution/run-tests', icon: <RunIcon fontSize="small" /> },
        {
          label: 'Run Campaigns',
          path: '/test-execution/run-campaigns',
          icon: <CampaignIcon fontSize="small" />,
        },
        {
          label: 'Deployments',
          path: '/test-execution/deployments',
          icon: <RunIcon fontSize="small" />,
        },
      ],
    },
    {
      sectionLabel: 'Reporting',
      items: [
        {
          label: 'Test Reports',
          path: '/test-results/reports',
          icon: <ReportsIcon fontSize="small" />,
        },
        {
          label: 'Campaign Reports',
          path: '/test-results/campaign-reports',
          icon: <CampaignIcon fontSize="small" />,
        },
        {
          label: 'Model Reports',
          path: '/test-results/model-reports',
          icon: <ModelIcon fontSize="small" />,
        },
        {
          label: 'Dependency Report',
          path: '/test-results/dependency-report',
          icon: <LinkIcon fontSize="small" />,
        },
      ],
    },
  ];

  const monitoringItems = [
    {
      label: 'Incidents',
      path: '/monitoring/incidents',
      icon: <IncidentIcon fontSize="small" />,
    },
    {
      label: 'Heatmap',
      path: '/monitoring/heatmap',
      icon: <HeatmapIcon fontSize="small" />,
    },
    {
      label: 'AI Queue',
      path: '/monitoring/ai-queue',
      icon: <DashboardIcon fontSize="small" />,
    },
  ];

  const configurationItems = [
    {
      label: 'Device',
      path: '/configuration/devices',
      icon: <DevicesIcon fontSize="small" />,
    },
    {
      label: 'Models',
      path: '/configuration/models',
      icon: <ModelIcon fontSize="small" />,
    },
    {
      label: 'Controller',
      path: '/configuration/controller',
      icon: <ControllerIcon fontSize="small" />,
    },
    { label: 'Library', path: '/configuration/library', icon: <LibraryIcon fontSize="small" /> },
    {
      label: 'Environment',
      path: '/configuration/environment',
      icon: <SettingsIcon fontSize="small" />,
    },
    {
      label: 'Notifications',
      path: '/configuration/notifications',
      icon: <NotificationsIcon fontSize="small" />,
    },
    {
      label: 'Remote Test',
      path: '/remote-test',
      icon: <TestingIcon fontSize="small" />,
    },
    {
      label: 'OpenRouter Debug',
      path: '/configuration/openrouter',
      icon: <AIIcon fontSize="small" />,
    },
    {
      label: 'API Testing',
      path: '/configuration/api-testing',
      icon: <ApiIcon fontSize="small" />,
    },
  ];

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {/* Dashboard - Simple button */}
      <Button
        component={Link}
        to="/"
        sx={{
          color: location.pathname === '/' ? 'secondary.main' : 'inherit',
          fontWeight: location.pathname === '/' ? 600 : 400,
          textTransform: 'none',
          px: 2,
          py: 1,
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        Dashboard
      </Button>

      {/* Rec - Simple button */}
      <Button
        component={Link}
        to="/rec"
        startIcon={<MonitorIcon fontSize="small" />}
        sx={{
          color: location.pathname === '/rec' ? 'secondary.main' : 'inherit',
          fontWeight: location.pathname === '/rec' ? 600 : 400,
          textTransform: 'none',
          px: 2,
          py: 1,
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        Rec
      </Button>

      {/* Test Grouped Dropdown (Plan, Execution, Results) */}
      <NavigationGroupedDropdown label="Test" groups={testGroups} />

      {/* User Interface - Standalone button */}
      <Button
        component={Link}
        to="/configuration/interface"
        startIcon={<TreeIcon fontSize="small" />}
        sx={{
          color: location.pathname.startsWith('/configuration/interface') ? 'secondary.main' : 'inherit',
          fontWeight: location.pathname.startsWith('/configuration/interface') ? 600 : 400,
          textTransform: 'none',
          px: 2,
          py: 1,
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        Interface
      </Button>

      {/* Monitoring Dropdown */}
      <NavigationDropdown label="Monitoring" items={monitoringItems} />

      {/* Grafana Dashboard - Simple button */}
      <Button
        component={Link}
        to="/grafana-dashboard"
        startIcon={<DashboardIcon fontSize="small" />}
        sx={{
          color: location.pathname === '/grafana-dashboard' ? 'secondary.main' : 'inherit',
          fontWeight: location.pathname === '/grafana-dashboard' ? 600 : 400,
          textTransform: 'none',
          px: 2,
          py: 1,
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        Grafana
      </Button>

      {/* Configuration Dropdown */}
      <NavigationDropdown label="Configuration" items={configurationItems} />
    </Box>
  );
};

export default NavigationBar;
