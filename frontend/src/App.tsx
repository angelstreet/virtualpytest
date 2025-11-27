import { Science } from '@mui/icons-material';
import { Container, AppBar, Toolbar, Typography, Box, CircularProgress } from '@mui/material';
import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Import navigation components (keep these as regular imports since they're always needed)
import Footer from './components/common/Footer';
import NavigationBar from './components/common/Navigation_Bar';
import { ServerSelector } from './components/common/ServerSelector';
import ThemeToggle from './components/common/ThemeToggle';
import { MCPTaskInput } from './components/mcp/MCPTaskInput';
import { HostManagerProvider } from './contexts/HostManagerProvider';
import { ServerManagerProvider } from './contexts/ServerManagerProvider';
import { ToastProvider } from './contexts/ToastContext';
import { BuilderProvider } from './contexts/builder/BuilderContext';

// Lazy load all pages for better performance and to avoid loading everything at once
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Rec = React.lazy(() => import('./pages/Rec'));
const CampaignEditor = React.lazy(() => import('./pages/CampaignEditor'));
const Requirements = React.lazy(() => import('./pages/Requirements'));
const Coverage = React.lazy(() => import('./pages/Coverage'));
const Models = React.lazy(() => import('./pages/Models'));
const GrafanaDashboard = React.lazy(() => import('./pages/GrafanaDashboard'));
const RunTests = React.lazy(() => import('./pages/RunTests'));
const RunCampaigns = React.lazy(() => import('./pages/RunCampaigns'));
const CampaignBuilder = React.lazy(() => import('./pages/CampaignBuilder'));
const Deployments = React.lazy(() => import('./pages/Deployments'));
const TestReports = React.lazy(() => import('./pages/TestReports'));
const CampaignReports = React.lazy(() => import('./pages/CampaignReports'));
const ModelReports = React.lazy(() => import('./pages/ModelReports'));
const DependencyReport = React.lazy(() => import('./pages/DependencyReport'));
const MonitoringIncidents = React.lazy(() => import('./pages/MonitoringIncidents'));
const Heatmap = React.lazy(() => import('./pages/Heatmap'));
const UserInterface = React.lazy(() => import('./pages/UserInterface'));
const TestCaseEditor = React.lazy(() => import('./pages/TestCaseEditor'));
const TestCaseBuilder = React.lazy(() => import('./pages/TestCaseBuilder'));
const NavigationEditor = React.lazy(() => import('./pages/NavigationEditor'));
const RemoteTestPage = React.lazy(() => import('./pages/RemoteTestPage'));
const AIQueueMonitor = React.lazy(() => import('./pages/AIQueueMonitor'));
const HLSDebugPage = React.lazy(() => import('./pages/HLSDebugPage'));
const OpenRouterDebug = React.lazy(() => import('./pages/OpenRouterDebug'));
const ApiTestingPage = React.lazy(() => import('./pages/ApiTestingPage'));
const Settings = React.lazy(() => import('./pages/Settings'));
const MCPPlayground = React.lazy(() => import('./pages/MCPPlayground'));
const GrafanaRedirect = React.lazy(() => import('./pages/GrafanaRedirect'));
const ApiDocumentation = React.lazy(() => import('./pages/ApiDocumentation'));
const PostmanWorkspace = React.lazy(() => import('./pages/PostmanWorkspace'));
const UserApiWorkspaces = React.lazy(() => import('./pages/UserApiWorkspaces'));
const UserApiWorkspaceDetail = React.lazy(() => import('./pages/UserApiWorkspaceDetail'));
const JiraIntegration = React.lazy(() => import('./pages/JiraIntegration'));

// 404 Not Found component
const NotFound: React.FC = () => {
  // Set document title for 404 pages
  React.useEffect(() => {
    document.title = '404 - Page Not Found | VirtualPyTest';

    // Set HTTP status to 404 if running on server
    if (typeof window !== 'undefined' && window.history) {
      // This helps with SEO and proper status codes
      const meta = document.createElement('meta');
      meta.name = 'robots';
      meta.content = 'noindex';
      document.head.appendChild(meta);

      return () => {
        document.head.removeChild(meta);
      };
    }
  }, []);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        textAlign: 'center',
        gap: 3,
      }}
    >
      <Typography
        variant="h1"
        component="h1"
        sx={{ fontSize: '6rem', fontWeight: 'bold', color: 'error.main' }}
      >
        404
      </Typography>
      <Typography variant="h4" component="h2" gutterBottom>
        Page Not Found
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ maxWidth: '500px', mb: 3 }}>
        The page you are looking for doesn't exist or has been moved.
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Typography
          component="a"
          href="/"
          sx={{
            textDecoration: 'none',
            color: 'primary.main',
            '&:hover': { textDecoration: 'underline' },
          }}
        >
          ← Back to Dashboard
        </Typography>
      </Box>
    </Box>
  );
};

// Loading component for Suspense fallback
const LoadingSpinner: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '200px',
      flexDirection: 'column',
      gap: 2,
    }}
  >
    <CircularProgress />
    <Typography variant="body2" color="textSecondary">
      Loading...
    </Typography>
  </Box>
);

const App: React.FC = () => {
  // Detect if app is running under a proxy path (e.g., /pi4/)
  // Check if current path starts with /piX/ pattern
  const getBasename = () => {
    const path = window.location.pathname;
    const proxyMatch = path.match(/^\/(pi\d+|mac)\//);
    return proxyMatch ? proxyMatch[0].slice(0, -1) : '';  // Return /pi4 (without trailing slash)
  };
  
  return (
        <Router basename={getBasename()}>
      <ToastProvider>
        <BuilderProvider>
          <ServerManagerProvider>
            <HostManagerProvider>
              <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
            <AppBar position="static" elevation={1}>
              <Toolbar>
                <Science sx={{ mr: 2 }} />
                <Typography variant="h6" component="div" sx={{ mr: 3 }}>
                  VirtualPyTest
                </Typography>
                <ServerSelector size="small" minWidth={160} />
                <Box sx={{ display: 'flex', alignItems: 'center', ml: 2, mr: 2 }}>
                  <NavigationBar />
                </Box>
                <ThemeToggle />
              </Toolbar>
            </AppBar>
            <Container
              maxWidth="lg"
              sx={{
                mt: 2,
                mb: 2,
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'stretch',
              }}
            >
              <Suspense fallback={<LoadingSpinner />}>
                <Routes>
                  {/* Dashboard */}
                  <Route path="/" element={<Dashboard />} />

                  {/* Rec Page */}
                  <Route path="/rec" element={<Rec />} />

                  {/* Builder Routes */}
                  <Route path="/builder/test-builder" element={<TestCaseBuilder />} />
                  <Route path="/builder/campaign-builder" element={<CampaignBuilder />} />
                  <Route path="/builder/mcp-playground" element={<MCPPlayground />} />

                  {/* Test Plan Routes */}
                  <Route path="/test-plan/test-cases" element={<TestCaseEditor />} />
                  <Route path="/test-plan/testcase-builder" element={<TestCaseBuilder />} /> {/* Legacy redirect */}
                  <Route path="/test-plan/campaigns" element={<CampaignEditor />} />
                  <Route path="/test-plan/requirements" element={<Requirements />} />
                  <Route path="/test-plan/coverage" element={<Coverage />} />

                  {/* Test Execution Routes */}
                  <Route path="/test-execution/run-tests" element={<RunTests />} />
                  <Route path="/test-execution/run-campaigns" element={<RunCampaigns />} />
                  <Route path="/campaign-builder" element={<CampaignBuilder />} /> {/* Legacy redirect */}
                  <Route path="/test-execution/deployments" element={<Deployments />} />

                  {/* Monitoring Routes */}
                  <Route path="/monitoring/system" element={<GrafanaDashboard />} />
                  <Route path="/monitoring/incidents" element={<MonitoringIncidents />} />
                  <Route path="/monitoring/heatmap" element={<Heatmap />} />
                  <Route path="/monitoring/ai-queue" element={<AIQueueMonitor />} />

                  {/* Test Results Routes */}
                  <Route path="/test-results/reports" element={<TestReports />} />
                  <Route path="/test-results/campaign-reports" element={<CampaignReports />} />
                  <Route path="/test-results/model-reports" element={<ModelReports />} />
                  <Route path="/test-results/dependency-report" element={<DependencyReport />} />

                  {/* Grafana Dashboard Route */}
                  <Route path="/grafana-dashboard" element={<GrafanaDashboard />} />
                  
                  {/* Grafana Direct Access - Redirects to VITE_GRAFANA_URL */}
                  <Route path="/grafana/*" element={<GrafanaRedirect />} />

                  {/* User API Testing Routes */}
                  <Route path="/api/workspaces" element={<UserApiWorkspaces />} />
                  <Route path="/api/workspace/:workspaceId" element={<UserApiWorkspaceDetail />} />
                  
                  {/* VirtualPyTest Documentation Routes */}
                  <Route path="/docs/api" element={<ApiDocumentation />} />
                  <Route path="/docs/postman" element={<PostmanWorkspace />} />

                  {/* Integrations Routes */}
                  <Route path="/integrations/jira" element={<JiraIntegration />} />

                  {/* Configuration Routes */}
                  <Route
                    path="/configuration"
                    element={<Navigate to="/configuration/models" replace />}
                  />
                  <Route
                    path="/configuration/"
                    element={<Navigate to="/configuration/models" replace />}
                  />
                  <Route path="/configuration/models" element={<Models />} />
                  <Route path="/configuration/interface" element={<UserInterface />} />
                  <Route path="/configuration/settings" element={<Settings />} />
                  <Route path="/configuration/openrouter" element={<OpenRouterDebug />} />
                  <Route path="/configuration/api-testing" element={<ApiTestingPage />} />

                  {/* Navigation Editor Route */}
                  <Route
                    path="/navigation-editor/:treeName/:treeId"
                    element={<NavigationEditor />}
                  />
                  <Route path="/navigation-editor/:treeName" element={<NavigationEditor />} />

                  {/* Remote Testing Route */}
                  <Route path="/remote-test" element={<RemoteTestPage />} />

                  {/* Debug Routes */}
                  <Route path="/debug/hls" element={<HLSDebugPage />} />

                  {/* Catch-all route for 404 */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </Container>

            {/* MCP Task Input - Global overlay component */}
            <MCPTaskInput />

            <Footer />
          </Box>
          </HostManagerProvider>
        </ServerManagerProvider>
        </BuilderProvider>
      </ToastProvider>
    </Router>
  );
};

export default App;
