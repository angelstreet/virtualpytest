import { Science } from '@mui/icons-material';
import { Container, AppBar, Toolbar, Typography, Box, CircularProgress } from '@mui/material';
import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';

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

// Auth components and providers
import { AuthProvider } from './contexts/auth/AuthContext';
import { PermissionProvider } from './contexts/auth/PermissionContext';
import { LoginPage, ProtectedRoute, AuthCallback } from './components/auth';
import { UserMenu } from './components/auth/UserMenu';
import { useAuth } from './hooks/auth/useAuth';
import { isAuthEnabled } from './lib/supabase';

// Lazy load all pages for better performance and to avoid loading everything at once
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Rec = React.lazy(() => import('./pages/Rec'));
const Documentation = React.lazy(() => import('./pages/Documentation'));
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
const UserApiWorkspaces = React.lazy(() => import('./pages/UserApiWorkspaces'));
const UserApiWorkspaceDetail = React.lazy(() => import('./pages/UserApiWorkspaceDetail'));
const JiraIntegration = React.lazy(() => import('./pages/JiraIntegration'));
const Teams = React.lazy(() => import('./pages/Teams'));
const Users = React.lazy(() => import('./pages/Users'));

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

// Header component that checks auth state
const AppHeader: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();

  // Hide header on login and callback pages
  const isAuthPage = location.pathname === '/login' || location.pathname === '/auth/callback';
  
  // Show header if: auth disabled OR user authenticated OR not on auth pages
  const shouldShowHeader = !isAuthEnabled || (isAuthenticated && !isAuthPage);

  if (isAuthPage || isLoading) {
    // Minimal header for login page
    return (
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Science sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            VirtualPyTest
          </Typography>
          <ThemeToggle />
        </Toolbar>
      </AppBar>
    );
  }

  if (!shouldShowHeader) {
    return null;
  }

  // Full header with navigation
  return (
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
        <Box sx={{ flexGrow: 1 }} />
        <ThemeToggle />
        <Box sx={{ ml: 2 }}>
          <UserMenu />
        </Box>
      </Toolbar>
    </AppBar>
  );
};

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
      <AuthProvider>
        <PermissionProvider>
          <ToastProvider>
            <BuilderProvider>
              <ServerManagerProvider>
                <HostManagerProvider>
                  <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
                <AppHeader />
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
                  {/* Public Routes - Only login and OAuth callback */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/auth/callback" element={<AuthCallback />} />

                  {/* All other routes require authentication */}
                  <Route element={<ProtectedRoute />}>
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

                  {/* User API Testing Routes - Protected by permission */}
                  <Route element={<ProtectedRoute requiredPermission="api_testing" />}>
                    <Route path="/api/workspaces" element={<UserApiWorkspaces />} />
                    <Route path="/api/workspace/:workspaceId" element={<UserApiWorkspaceDetail />} />
                  </Route>
                  
                  {/* VirtualPyTest Documentation Routes */}
                  <Route path="/docs/api" element={<ApiDocumentation />} />
                  <Route path="/docs/:section" element={<Documentation />} />
                  <Route path="/docs/:section/:page" element={<Documentation />} />

                  {/* Integrations Routes - Protected by permission */}
                  <Route element={<ProtectedRoute requiredPermission="jira_integration" />}>
                    <Route path="/integrations/jira" element={<JiraIntegration />} />
                  </Route>

                  {/* Teams & Users Management - Admin only */}
                  <Route element={<ProtectedRoute requiredRole="admin" />}>
                    <Route path="/teams" element={<Teams />} />
                    <Route path="/users" element={<Users />} />
                  </Route>

                  {/* Configuration Routes */}
                  <Route
                    path="/configuration"
                    element={<Navigate to="/configuration/models" replace />}
                  />
                  <Route
                    path="/configuration/"
                    element={<Navigate to="/configuration/models" replace />}
                  />
                  
                  {/* Admin-only configuration routes */}
                  <Route element={<ProtectedRoute requiredRole="admin" />}>
                    <Route path="/configuration/models" element={<Models />} />
                    <Route path="/configuration/settings" element={<Settings />} />
                  </Route>
                  
                  {/* Regular configuration routes */}
                  <Route path="/configuration/interface" element={<UserInterface />} />
                  <Route path="/configuration/openrouter" element={<OpenRouterDebug />} />
                  
                  {/* API Testing - requires permission */}
                  <Route element={<ProtectedRoute requiredPermission="api_testing" />}>
                    <Route path="/configuration/api-testing" element={<ApiTestingPage />} />
                  </Route>

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
                  </Route>
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
        </PermissionProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;
