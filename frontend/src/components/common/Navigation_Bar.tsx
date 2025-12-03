import {
  Science as TestIcon,
  Campaign as CampaignIcon,
  PlayArrow as RunIcon,
  Visibility as MonitorIcon,
  Assessment as ReportsIcon,
  AccountTree as TreeIcon,
  Settings as SettingsIcon,
  Assignment as RequirementIcon,
  TrendingUp as CoverageIcon,
  Memory as ModelIcon,
  BugReport as TestingIcon,
  Link as LinkIcon,
  Warning as IncidentIcon,
  GridView as HeatmapIcon,
  Dashboard as DashboardIcon,
  SmartToy as AIIcon,
  Api as ApiIcon,
  Build as BuildIcon, // For Builder section
  SmartToy, // For MCP Playground
  Extension as IntegrationIcon, // For Integrations section
  Security as SecurityIcon, // For Security Reports
  LocalPostOffice as PostmanIcon, // For Postman integration
  HelpOutline as FaqIcon, // For FAQ
  PhotoLibrary as ScreenshotsIcon, // For Screenshots
  VideoLibrary as VideosIcon, // For Videos
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
        { label: 'MCP Playground', path: '/builder/mcp-playground', icon: <SmartToy fontSize="small" /> },
      ],
    },
    {
      sectionLabel: 'Test Plan',
      items: [
        { label: 'Test Cases', path: '/test-plan/test-cases', icon: <TestIcon fontSize="small" /> },
        { label: 'Campaigns', path: '/test-plan/campaigns', icon: <CampaignIcon fontSize="small" /> },
        {
          label: 'Requirements',
          path: '/test-plan/requirements',
          icon: <RequirementIcon fontSize="small" />,
        },
        {
          label: 'Coverage',
          path: '/test-plan/coverage',
          icon: <CoverageIcon fontSize="small" />,
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

  // VirtualPyTest Documentation menu items
  const docsItems = [
    {
      label: 'Get Started',
      path: '/docs/get-started',
      icon: <RunIcon fontSize="small" />,
    },
    {
      label: 'FAQ',
      path: '/docs/faq',
      icon: <FaqIcon fontSize="small" />,
    },
    {
      label: 'Features',
      path: '/docs/features',
      icon: <TestingIcon fontSize="small" />,
    },
    {
      label: 'User Guide',
      path: '/docs/user-guide',
      icon: <RequirementIcon fontSize="small" />,
    },
    {
      label: 'Technical Docs',
      path: '/docs/technical',
      icon: <BuildIcon fontSize="small" />,
    },
    {
      label: 'Security Reports',
      path: '/docs/security',
      icon: <SecurityIcon fontSize="small" />,
    },
    {
      label: 'API Reference',
      path: '/docs/api',
      icon: <ApiIcon fontSize="small" />,
    },
    {
      label: 'Examples',
      path: '/docs/examples',
      icon: <TreeIcon fontSize="small" />,
    },
    {
      label: 'Screenshots',
      path: '/docs/screenshots',
      icon: <ScreenshotsIcon fontSize="small" />,
    },
    {
      label: 'Videos',
      path: '/docs/videos',
      icon: <VideosIcon fontSize="small" />,
    },
  ];

  // Third-party Integrations menu items
  const integrationsItems = [
    {
      label: 'Grafana',
      path: '/grafana-dashboard',
      icon: <DashboardIcon fontSize="small" />,
    },
    {
      label: 'Postman',
      path: '/api/workspaces',
      icon: <PostmanIcon fontSize="small" />,
    },
    {
      label: 'Jira',
      path: '/integrations/jira',
      icon: <IntegrationIcon fontSize="small" />,
    },
  ];

  const configurationItems = [
    {
      label: 'Models',
      path: '/configuration/models',
      icon: <ModelIcon fontSize="small" />,
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
      label: 'Settings',
      path: '/configuration/settings',
      icon: <SettingsIcon fontSize="small" />,
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

      {/* Docs Dropdown (VirtualPyTest Documentation) */}
      <NavigationDropdown label="Docs" items={docsItems} />

      {/* Integrations Dropdown (Third-party Tools) */}
      <NavigationDropdown label="Plugins" items={integrationsItems} />

      {/* Configuration Dropdown */}
      <NavigationDropdown label="Settings" items={configurationItems} />
    </Box>
  );
};

export default NavigationBar;
