export type Role = 'admin' | 'tester' | 'viewer';

export type Permission =
  | 'view_dashboard'
  | 'run_tests'
  | 'create_test_cases'
  | 'edit_test_cases'
  | 'delete_test_cases'
  | 'view_reports'
  | 'api_testing'
  | 'jira_integration'
  | 'manage_devices'
  | 'manage_settings'
  | 'manage_users'
  | 'view_monitoring'
  | 'create_campaigns'
  | 'edit_campaigns'
  | 'delete_campaigns';

export interface UserProfile {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  role: Role;
  permissions: Permission[];
  created_at: string;
  updated_at: string;
}

export interface AuthUser {
  id: string;
  email: string | null;
  user_metadata?: {
    full_name?: string;
    avatar_url?: string;
  };
}

// Role-based permission mapping
export const ROLE_PERMISSIONS: Record<Role, Permission[] | ['*']> = {
  admin: ['*'], // All permissions
  tester: [
    'view_dashboard',
    'run_tests',
    'create_test_cases',
    'edit_test_cases',
    'view_reports',
    'api_testing',
    'jira_integration',
    'manage_devices',
    'view_monitoring',
    'create_campaigns',
    'edit_campaigns',
  ],
  viewer: ['view_dashboard', 'view_reports', 'view_monitoring'],
};

// Page-level permission requirements
export const PAGE_PERMISSIONS: Record<string, Permission | Role | null> = {
  '/': null, // Public
  '/login': null, // Public
  '/configuration/settings': 'manage_settings',
  '/configuration/models': 'admin',
  '/api/workspaces': 'api_testing',
  '/integrations/jira': 'jira_integration',
  '/test-execution/run-tests': 'run_tests',
  '/test-execution/run-campaigns': 'run_tests',
  '/test-plan/test-cases': 'view_dashboard',
  '/test-plan/campaigns': 'view_dashboard',
  '/builder/test-builder': 'create_test_cases',
  '/builder/campaign-builder': 'create_campaigns',
};

