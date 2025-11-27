import React, { createContext, useContext, useMemo } from 'react';
import { useAuthContext } from './AuthContext';
import { Permission, Role, ROLE_PERMISSIONS } from '../../types/auth';

interface PermissionContextType {
  role: Role | null;
  permissions: Permission[];
  hasRole: (requiredRole: Role | Role[]) => boolean;
  hasPermission: (permission: Permission) => boolean;
  canAccess: (permission: Permission | Permission[]) => boolean;
}

const PermissionContext = createContext<PermissionContextType | undefined>(undefined);

export const usePermissionContext = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissionContext must be used within PermissionProvider');
  }
  return context;
};

interface PermissionProviderProps {
  children: React.ReactNode;
}

export const PermissionProvider: React.FC<PermissionProviderProps> = ({ children }) => {
  const { profile, isAuthenticated } = useAuthContext();

  // Compute effective permissions based on role and profile
  const { role, permissions } = useMemo(() => {
    if (!isAuthenticated || !profile) {
      return { role: null, permissions: [] as Permission[] };
    }

    const userRole = profile.role;
    const rolePerms = ROLE_PERMISSIONS[userRole];

    // Admin has all permissions
    if (rolePerms.includes('*')) {
      return {
        role: userRole,
        permissions: [
          'view_dashboard',
          'run_tests',
          'create_test_cases',
          'edit_test_cases',
          'delete_test_cases',
          'view_reports',
          'api_testing',
          'jira_integration',
          'manage_devices',
          'manage_settings',
          'manage_users',
          'view_monitoring',
          'create_campaigns',
          'edit_campaigns',
          'delete_campaigns',
        ] as Permission[],
      };
    }

    // Merge role permissions with custom profile permissions
    const allPermissions = new Set([
      ...(rolePerms as Permission[]),
      ...(profile.permissions || []),
    ]);

    return {
      role: userRole,
      permissions: Array.from(allPermissions) as Permission[],
    };
  }, [profile, isAuthenticated]);

  // Check if user has a specific role
  const hasRole = (requiredRole: Role | Role[]): boolean => {
    if (!role) return false;

    if (Array.isArray(requiredRole)) {
      return requiredRole.includes(role);
    }

    return role === requiredRole;
  };

  // Check if user has a specific permission
  const hasPermission = (permission: Permission): boolean => {
    if (!isAuthenticated) return false;
    return permissions.includes(permission);
  };

  // Check if user can access (has permission or role)
  const canAccess = (requirement: Permission | Permission[]): boolean => {
    if (!isAuthenticated) return false;

    if (Array.isArray(requirement)) {
      // User needs at least one of the permissions
      return requirement.some((perm) => permissions.includes(perm));
    }

    return permissions.includes(requirement);
  };

  const value: PermissionContextType = {
    role,
    permissions,
    hasRole,
    hasPermission,
    canAccess,
  };

  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>;
};

