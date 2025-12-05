/**
 * AI Page Schema Registry
 * 
 * Defines what elements are controllable on each page for AI-driven interactions.
 * The AI can query this schema to understand available actions without hard-coding each one.
 */

export interface PageElement {
  id: string;
  type: 'button' | 'table' | 'dropdown' | 'input' | 'grid' | 'modal' | 'filter' | 'stepper' | 'stream' | 'chart';
  label: string;
  actions: string[];
  dataSource?: string; // Hook or API to get data
  params?: Record<string, string>; // Parameters the action accepts
}

export interface PageSchema {
  path: string;
  name: string;
  description: string;
  elements: PageElement[];
  quickActions?: string[]; // Common AI shortcuts for this page
}

export const PAGE_SCHEMAS: Record<string, PageSchema> = {
  // =====================
  // DASHBOARD
  // =====================
  '/': {
    path: '/',
    name: 'Dashboard',
    description: 'Overview of system status, hosts, devices, and recent activity',
    elements: [
      { id: 'host-accordion', type: 'grid', label: 'Host Status Cards', actions: ['expand', 'collapse', 'select'] },
      { id: 'refresh-btn', type: 'button', label: 'Refresh Data', actions: ['click'] },
      { id: 'restart-service-btn', type: 'button', label: 'Restart Service', actions: ['click'], params: { host_name: 'string' } },
      { id: 'restart-stream-btn', type: 'button', label: 'Restart Streams', actions: ['click'] },
      { id: 'reboot-btn', type: 'button', label: 'Reboot Host', actions: ['click'], params: { host_name: 'string' } },
    ],
    quickActions: ['show_host_status', 'restart_all_streams', 'check_device_health'],
  },

  // =====================
  // DEVICE CONTROL (REC)
  // =====================
  '/device-control': {
    path: '/device-control',
    name: 'Device Control',
    description: 'View and control connected devices with live streams',
    elements: [
      { id: 'device-grid', type: 'grid', label: 'Device Preview Grid', actions: ['select_device', 'open_stream'] },
      { id: 'host-filter', type: 'dropdown', label: 'Filter by Host', actions: ['select'], params: { host_name: 'string' } },
      { id: 'model-filter', type: 'dropdown', label: 'Filter by Model', actions: ['select'], params: { model: 'string' } },
      { id: 'flag-filter', type: 'dropdown', label: 'Filter by Flag', actions: ['select'], params: { flag: 'string' } },
      { id: 'stream-modal', type: 'modal', label: 'Device Stream Modal', actions: ['open', 'close'] },
      { id: 'refresh-btn', type: 'button', label: 'Refresh Streams', actions: ['click'] },
    ],
    quickActions: ['show_device', 'open_device_stream', 'filter_by_host'],
  },

  // =====================
  // TEST EXECUTION
  // =====================
  '/test-execution/run-tests': {
    path: '/test-execution/run-tests',
    name: 'Run Tests',
    description: 'Execute test cases and scripts on devices',
    elements: [
      { id: 'host-selector', type: 'dropdown', label: 'Select Host', actions: ['select'], params: { host_name: 'string' } },
      { id: 'device-selector', type: 'dropdown', label: 'Select Device', actions: ['select'], params: { device_id: 'string' } },
      { id: 'script-selector', type: 'dropdown', label: 'Select Script/TestCase', actions: ['select', 'search'], params: { script_name: 'string' } },
      { id: 'userinterface-selector', type: 'dropdown', label: 'Select User Interface', actions: ['select'], params: { interface_id: 'string' } },
      { id: 'run-btn', type: 'button', label: 'Run Test', actions: ['click'] },
      { id: 'execution-table', type: 'table', label: 'Execution History', actions: ['view_details', 'open_report', 'open_logs'] },
      { id: 'device-stream', type: 'stream', label: 'Live Device Stream', actions: ['play', 'pause', 'fullscreen'] },
    ],
    quickActions: ['run_test', 'show_execution_status', 'view_report'],
  },

  '/test-execution/run-campaigns': {
    path: '/test-execution/run-campaigns',
    name: 'Run Campaigns',
    description: 'Execute multi-device test campaigns',
    elements: [
      { id: 'campaign-stepper', type: 'stepper', label: 'Campaign Setup Wizard', actions: ['next', 'back', 'goto_step'], params: { step: 'number' } },
      { id: 'script-sequence', type: 'table', label: 'Script Sequence Builder', actions: ['add_script', 'remove_script', 'reorder'] },
      { id: 'device-assignment', type: 'grid', label: 'Device Assignment', actions: ['assign', 'unassign'] },
      { id: 'launch-btn', type: 'button', label: 'Launch Campaign', actions: ['click'] },
      { id: 'history-table', type: 'table', label: 'Campaign History', actions: ['view_details', 'open_report'] },
    ],
    quickActions: ['create_campaign', 'launch_campaign', 'view_campaign_history'],
  },

  // =====================
  // TEST PLAN
  // =====================
  '/test-plan/test-cases': {
    path: '/test-plan/test-cases',
    name: 'Test Cases',
    description: 'Manage and organize test cases',
    elements: [
      { id: 'testcase-table', type: 'table', label: 'Test Case List', actions: ['select', 'edit', 'delete', 'duplicate', 'filter'] },
      { id: 'interface-filter', type: 'dropdown', label: 'Filter by Interface', actions: ['select'], params: { interface_id: 'string' } },
      { id: 'status-filter', type: 'dropdown', label: 'Filter by Status', actions: ['select'], params: { status: 'active|inactive' } },
      { id: 'create-btn', type: 'button', label: 'Create Test Case', actions: ['click'] },
      { id: 'search-input', type: 'input', label: 'Search Test Cases', actions: ['type', 'clear'], params: { query: 'string' } },
    ],
    quickActions: ['list_testcases', 'create_testcase', 'search_testcase'],
  },

  '/test-plan/campaigns': {
    path: '/test-plan/campaigns',
    name: 'Campaigns',
    description: 'Manage test campaign definitions',
    elements: [
      { id: 'campaign-table', type: 'table', label: 'Campaign List', actions: ['select', 'edit', 'delete', 'run'] },
      { id: 'create-btn', type: 'button', label: 'Create Campaign', actions: ['click'] },
    ],
    quickActions: ['list_campaigns', 'create_campaign'],
  },

  '/test-plan/requirements': {
    path: '/test-plan/requirements',
    name: 'Requirements',
    description: 'Track test requirements and coverage',
    elements: [
      { id: 'requirements-table', type: 'table', label: 'Requirements List', actions: ['select', 'edit', 'link_testcase'] },
      { id: 'import-btn', type: 'button', label: 'Import Requirements', actions: ['click'] },
    ],
    quickActions: ['list_requirements', 'check_coverage'],
  },

  // =====================
  // MONITORING
  // =====================
  '/monitoring/incidents': {
    path: '/monitoring/incidents',
    name: 'Incidents',
    description: 'View and manage monitoring alerts and incidents',
    elements: [
      { id: 'active-alerts-table', type: 'table', label: 'Active Alerts', actions: ['expand', 'validate', 'discard', 'view_freeze'] },
      { id: 'closed-alerts-table', type: 'table', label: 'Closed Alerts', actions: ['expand', 'view_details'] },
      { id: 'detail-toggle', type: 'button', label: 'Toggle Detailed View', actions: ['click'] },
      { id: 'clear-all-btn', type: 'button', label: 'Clear All Alerts', actions: ['click'] },
      { id: 'freeze-modal', type: 'modal', label: 'Freeze Details Modal', actions: ['open', 'close'] },
    ],
    quickActions: ['show_active_alerts', 'validate_alert', 'discard_alert'],
  },

  '/monitoring/heatmap': {
    path: '/monitoring/heatmap',
    name: 'Heatmap',
    description: 'Real-time device health monitoring with visual heatmap',
    elements: [
      { id: 'mosaic-player', type: 'stream', label: 'Mosaic Video Player', actions: ['play', 'pause', 'seek'] },
      { id: 'timeline-slider', type: 'input', label: 'Timeline Slider', actions: ['seek'], params: { index: 'number' } },
      { id: 'status-filter', type: 'filter', label: 'Status Filter', actions: ['select'], params: { status: 'ALL|OK|KO' } },
      { id: 'analysis-table', type: 'table', label: 'Device Analysis', actions: ['expand', 'view_freeze', 'open_stream'] },
      { id: 'history-panel', type: 'table', label: 'Heatmap History', actions: ['select_timestamp'] },
      { id: 'generate-report-btn', type: 'button', label: 'Generate Report', actions: ['click'] },
    ],
    quickActions: ['show_heatmap', 'show_incidents', 'generate_heatmap_report'],
  },

  '/monitoring/system': {
    path: '/monitoring/system',
    name: 'System Monitoring',
    description: 'Grafana dashboards for system metrics',
    elements: [
      { id: 'grafana-iframe', type: 'stream', label: 'Grafana Dashboard', actions: ['refresh', 'change_timerange'] },
    ],
    quickActions: ['show_system_metrics'],
  },

  '/monitoring/ai-queue': {
    path: '/monitoring/ai-queue',
    name: 'AI Queue Monitor',
    description: 'Monitor AI analysis queue and processing',
    elements: [
      { id: 'queue-table', type: 'table', label: 'Queue Items', actions: ['view_details', 'retry', 'delete'] },
      { id: 'stats-cards', type: 'grid', label: 'Queue Statistics', actions: ['refresh'] },
    ],
    quickActions: ['show_queue_status', 'retry_failed'],
  },

  // =====================
  // TEST RESULTS
  // =====================
  '/test-results/reports': {
    path: '/test-results/reports',
    name: 'Test Reports',
    description: 'View and analyze test execution reports',
    elements: [
      { id: 'reports-table', type: 'table', label: 'Reports List', actions: ['select', 'open_report', 'open_logs', 'validate', 'discard', 'filter'] },
      { id: 'detail-toggle', type: 'button', label: 'Toggle Detailed Columns', actions: ['click'] },
      { id: 'stats-cards', type: 'grid', label: 'Report Statistics', actions: [] },
      { id: 'discard-modal', type: 'modal', label: 'Discard Comment Modal', actions: ['open', 'close', 'submit'] },
    ],
    quickActions: ['show_failed_tests', 'show_recent_reports', 'analyze_report'],
  },

  '/test-results/campaign-reports': {
    path: '/test-results/campaign-reports',
    name: 'Campaign Reports',
    description: 'View campaign execution results and trends',
    elements: [
      { id: 'campaign-reports-table', type: 'table', label: 'Campaign Reports', actions: ['select', 'view_details', 'filter'] },
      { id: 'trend-chart', type: 'chart', label: 'Success Rate Trend', actions: ['change_timerange'] },
    ],
    quickActions: ['show_campaign_results', 'compare_campaigns'],
  },

  '/test-results/model-reports': {
    path: '/test-results/model-reports',
    name: 'Model Reports',
    description: 'Test results aggregated by device model',
    elements: [
      { id: 'model-reports-table', type: 'table', label: 'Model Statistics', actions: ['select', 'drill_down'] },
    ],
    quickActions: ['show_model_stats', 'compare_models'],
  },

  // =====================
  // BUILDER
  // =====================
  '/builder/test-builder': {
    path: '/builder/test-builder',
    name: 'Test Builder',
    description: 'Visual test case builder with drag-and-drop',
    elements: [
      { id: 'step-canvas', type: 'grid', label: 'Test Steps Canvas', actions: ['add_step', 'remove_step', 'reorder', 'edit_step'] },
      { id: 'action-palette', type: 'grid', label: 'Action Palette', actions: ['select_action'] },
      { id: 'save-btn', type: 'button', label: 'Save Test Case', actions: ['click'] },
      { id: 'run-btn', type: 'button', label: 'Run Test', actions: ['click'] },
      { id: 'device-preview', type: 'stream', label: 'Device Preview', actions: ['take_screenshot', 'inspect_element'] },
    ],
    quickActions: ['add_step', 'save_testcase', 'run_testcase'],
  },

  '/builder/campaign-builder': {
    path: '/builder/campaign-builder',
    name: 'Campaign Builder',
    description: 'Visual campaign builder',
    elements: [
      { id: 'campaign-canvas', type: 'grid', label: 'Campaign Flow Canvas', actions: ['add_testcase', 'remove_testcase', 'reorder'] },
      { id: 'testcase-palette', type: 'table', label: 'Available Test Cases', actions: ['select', 'drag'] },
      { id: 'save-btn', type: 'button', label: 'Save Campaign', actions: ['click'] },
    ],
    quickActions: ['add_testcase_to_campaign', 'save_campaign'],
  },

  // =====================
  // CONFIGURATION
  // =====================
  '/configuration/settings': {
    path: '/configuration/settings',
    name: 'Settings',
    description: 'System configuration and preferences',
    elements: [
      { id: 'settings-form', type: 'input', label: 'Settings Form', actions: ['edit', 'save'] },
      { id: 'save-btn', type: 'button', label: 'Save Settings', actions: ['click'] },
    ],
    quickActions: ['show_settings', 'update_setting'],
  },

  '/configuration/interface': {
    path: '/configuration/interface',
    name: 'User Interfaces',
    description: 'Manage app interfaces and navigation trees',
    elements: [
      { id: 'interface-table', type: 'table', label: 'Interface List', actions: ['select', 'edit', 'delete', 'duplicate'] },
      { id: 'create-btn', type: 'button', label: 'Create Interface', actions: ['click'] },
    ],
    quickActions: ['list_interfaces', 'create_interface'],
  },

  '/configuration/models': {
    path: '/configuration/models',
    name: 'AI Models',
    description: 'Configure AI models and providers',
    elements: [
      { id: 'models-table', type: 'table', label: 'Model Configurations', actions: ['select', 'edit', 'test'] },
      { id: 'add-model-btn', type: 'button', label: 'Add Model', actions: ['click'] },
    ],
    quickActions: ['list_models', 'test_model'],
  },

  // =====================
  // AI AGENT
  // =====================
  '/ai-agent': {
    path: '/ai-agent',
    name: 'AI Agent Chat',
    description: 'Interactive AI assistant for QA automation',
    elements: [
      { id: 'chat-input', type: 'input', label: 'Message Input', actions: ['type', 'send'] },
      { id: 'chat-history', type: 'table', label: 'Chat History', actions: ['scroll', 'copy'] },
      { id: 'mode-selector', type: 'dropdown', label: 'Agent Mode', actions: ['select'], params: { mode: 'qa_manager|device_controller|test_analyst' } },
    ],
    quickActions: ['send_message', 'clear_chat', 'change_mode'],
  },

  // =====================
  // ADMIN
  // =====================
  '/teams': {
    path: '/teams',
    name: 'Teams',
    description: 'Manage teams and permissions',
    elements: [
      { id: 'teams-table', type: 'table', label: 'Teams List', actions: ['select', 'edit', 'delete'] },
      { id: 'create-btn', type: 'button', label: 'Create Team', actions: ['click'] },
    ],
    quickActions: ['list_teams', 'create_team'],
  },

  '/users': {
    path: '/users',
    name: 'Users',
    description: 'Manage users and access',
    elements: [
      { id: 'users-table', type: 'table', label: 'Users List', actions: ['select', 'edit', 'delete', 'invite'] },
      { id: 'invite-btn', type: 'button', label: 'Invite User', actions: ['click'] },
    ],
    quickActions: ['list_users', 'invite_user'],
  },
};

/**
 * Get schema for a specific page path
 */
export function getPageSchema(path: string): PageSchema | undefined {
  // Exact match first
  if (PAGE_SCHEMAS[path]) {
    return PAGE_SCHEMAS[path];
  }
  
  // Check for partial matches (for parameterized routes)
  for (const [schemaPath, schema] of Object.entries(PAGE_SCHEMAS)) {
    if (path.startsWith(schemaPath)) {
      return schema;
    }
  }
  
  return undefined;
}

/**
 * Get all available pages for navigation
 */
export function getNavigablePages(): { path: string; name: string; description: string }[] {
  return Object.values(PAGE_SCHEMAS).map(({ path, name, description }) => ({
    path,
    name,
    description,
  }));
}

/**
 * Get quick actions for a page
 */
export function getPageQuickActions(path: string): string[] {
  const schema = getPageSchema(path);
  return schema?.quickActions || [];
}

/**
 * Search elements across all pages
 */
export function searchElements(query: string): { page: string; element: PageElement }[] {
  const results: { page: string; element: PageElement }[] = [];
  const lowerQuery = query.toLowerCase();
  
  for (const [path, schema] of Object.entries(PAGE_SCHEMAS)) {
    for (const element of schema.elements) {
      if (
        element.id.toLowerCase().includes(lowerQuery) ||
        element.label.toLowerCase().includes(lowerQuery) ||
        element.actions.some(a => a.toLowerCase().includes(lowerQuery))
      ) {
        results.push({ page: path, element });
      }
    }
  }
  
  return results;
}

