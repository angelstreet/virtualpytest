/**
 * Requirements Management Hook
 *
 * This hook handles requirements operations including:
 * - CRUD operations for requirements
 * - Linking requirements to testcases and scripts
 * - Filtering and searching requirements
 */

import { useState, useCallback, useEffect } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface Requirement {
  requirement_id: string;
  team_id: string;
  requirement_code: string;
  requirement_name: string;
  category: string;
  priority: string; // P1, P2, P3
  description?: string;
  acceptance_criteria?: string[];
  app_type: string; // streaming, social, news, all
  device_model: string; // android_mobile, android_tv, web, all
  status: string; // active, deprecated, draft
  source_document?: string;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
}

export interface RequirementFilters {
  category?: string;
  priority?: string;
  app_type?: string;
  device_model?: string;
  status?: string;
}

export interface UseRequirementsReturn {
  // Requirements List
  requirements: Requirement[];
  isLoading: boolean;
  error: string | null;
  
  // CRUD Operations
  createRequirement: (requirement: Omit<Requirement, 'requirement_id' | 'team_id' | 'created_at' | 'updated_at'>) => Promise<{ success: boolean; requirement_id?: string; error?: string }>;
  updateRequirement: (requirementId: string, updates: Partial<Requirement>) => Promise<{ success: boolean; error?: string }>;
  deleteRequirement: (requirementId: string) => Promise<{ success: boolean; error?: string }>;
  getRequirement: (requirementId: string) => Promise<Requirement | null>;
  getRequirementByCode: (requirementCode: string) => Promise<Requirement | null>;
  
  // List & Filter
  loadRequirements: (filters?: RequirementFilters) => Promise<void>;
  refreshRequirements: () => Promise<void>;
  
  // Filters
  filters: RequirementFilters;
  setFilters: (filters: RequirementFilters) => void;
  
  // Categories & Priorities
  categories: string[];
  priorities: string[];
  appTypes: string[];
  deviceModels: string[];
  
  // Linkage
  linkTestcase: (testcaseId: string, requirementId: string, coverageType?: string, notes?: string) => Promise<{ success: boolean; error?: string }>;
  unlinkTestcase: (testcaseId: string, requirementId: string) => Promise<{ success: boolean; error?: string }>;
  linkScript: (scriptName: string, requirementId: string, coverageType?: string, notes?: string) => Promise<{ success: boolean; error?: string }>;
  unlinkScript: (scriptName: string, requirementId: string) => Promise<{ success: boolean; error?: string }>;
  getTestcaseRequirements: (testcaseId: string) => Promise<Requirement[]>;
  getScriptRequirements: (scriptName: string) => Promise<Requirement[]>;
}

export const useRequirements = (): UseRequirementsReturn => {
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<RequirementFilters>({
    status: 'active'
  });
  
  // Static lists (can be made dynamic from backend later)
  const categories = ['playback', 'auth', 'navigation', 'search', 'ui', 'performance', 'accessibility'];
  const priorities = ['P1', 'P2', 'P3'];
  const appTypes = ['streaming', 'social', 'news', 'all'];
  const deviceModels = ['android_mobile', 'android_tv', 'web', 'all'];
  
  // Load requirements with filters
  const loadRequirements = useCallback(async (customFilters?: RequirementFilters) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const activeFilters = customFilters || filters;
      const params = new URLSearchParams();
      
      if (activeFilters.category) params.append('category', activeFilters.category);
      if (activeFilters.priority) params.append('priority', activeFilters.priority);
      if (activeFilters.app_type) params.append('app_type', activeFilters.app_type);
      if (activeFilters.device_model) params.append('device_model', activeFilters.device_model);
      if (activeFilters.status) params.append('status', activeFilters.status);
      
      const url = buildServerUrl(`/server/requirements/list${params.toString() ? `?${params.toString()}` : ''}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to load requirements: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setRequirements(data.requirements || []);
      } else {
        throw new Error(data.error || 'Failed to load requirements');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      console.error('[@useRequirements] Error loading requirements:', err);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);
  
  // Refresh current requirements
  const refreshRequirements = useCallback(() => {
    return loadRequirements(filters);
  }, [loadRequirements, filters]);
  
  // Create requirement
  const createRequirement = useCallback(async (requirement: Omit<Requirement, 'requirement_id' | 'team_id' | 'created_at' | 'updated_at'>) => {
    try {
      const url = buildServerUrl('/server/requirements/create');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requirement),
      });
      
      const data = await response.json();
      
      if (data.success) {
        await refreshRequirements();
        return { success: true, requirement_id: data.requirement_id };
      } else {
        return { success: false, error: data.error || 'Failed to create requirement' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error creating requirement:', err);
      return { success: false, error: errorMsg };
    }
  }, [refreshRequirements]);
  
  // Update requirement
  const updateRequirement = useCallback(async (requirementId: string, updates: Partial<Requirement>) => {
    try {
      const url = buildServerUrl(`/server/requirements/${requirementId}`);
      const response = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      
      const data = await response.json();
      
      if (data.success) {
        await refreshRequirements();
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Failed to update requirement' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error updating requirement:', err);
      return { success: false, error: errorMsg };
    }
  }, [refreshRequirements]);
  
  // Delete requirement (soft delete by setting status to deprecated)
  const deleteRequirement = useCallback(async (requirementId: string) => {
    return updateRequirement(requirementId, { status: 'deprecated' });
  }, [updateRequirement]);
  
  // Get single requirement by ID
  const getRequirement = useCallback(async (requirementId: string): Promise<Requirement | null> => {
    try {
      const url = buildServerUrl(`/server/requirements/${requirementId}`);
      const response = await fetch(url);
      
      const data = await response.json();
      
      if (data.success) {
        return data.requirement;
      } else {
        console.error('[@useRequirements] Error getting requirement:', data.error);
        return null;
      }
    } catch (err) {
      console.error('[@useRequirements] Error getting requirement:', err);
      return null;
    }
  }, []);
  
  // Get requirement by code
  const getRequirementByCode = useCallback(async (requirementCode: string): Promise<Requirement | null> => {
    try {
      const url = buildServerUrl(`/server/requirements/by-code/${requirementCode}`);
      const response = await fetch(url);
      
      const data = await response.json();
      
      if (data.success) {
        return data.requirement;
      } else {
        console.error('[@useRequirements] Error getting requirement by code:', data.error);
        return null;
      }
    } catch (err) {
      console.error('[@useRequirements] Error getting requirement by code:', err);
      return null;
    }
  }, []);
  
  // Link testcase to requirement
  const linkTestcase = useCallback(async (testcaseId: string, requirementId: string, coverageType = 'full', notes?: string) => {
    try {
      const url = buildServerUrl('/server/requirements/link-testcase');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          testcase_id: testcaseId,
          requirement_id: requirementId,
          coverage_type: coverageType,
          coverage_notes: notes,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Failed to link testcase' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error linking testcase:', err);
      return { success: false, error: errorMsg };
    }
  }, []);
  
  // Unlink testcase from requirement
  const unlinkTestcase = useCallback(async (testcaseId: string, requirementId: string) => {
    try {
      const url = buildServerUrl('/server/requirements/unlink-testcase');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          testcase_id: testcaseId,
          requirement_id: requirementId,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Failed to unlink testcase' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error unlinking testcase:', err);
      return { success: false, error: errorMsg };
    }
  }, []);
  
  // Link script to requirement
  const linkScript = useCallback(async (scriptName: string, requirementId: string, coverageType = 'full', notes?: string) => {
    try {
      const url = buildServerUrl('/server/requirements/link-script');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_name: scriptName,
          requirement_id: requirementId,
          coverage_type: coverageType,
          coverage_notes: notes,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Failed to link script' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error linking script:', err);
      return { success: false, error: errorMsg };
    }
  }, []);
  
  // Unlink script from requirement
  const unlinkScript = useCallback(async (scriptName: string, requirementId: string) => {
    try {
      const url = buildServerUrl('/server/requirements/unlink-script');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_name: scriptName,
          requirement_id: requirementId,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Failed to unlink script' };
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('[@useRequirements] Error unlinking script:', err);
      return { success: false, error: errorMsg };
    }
  }, []);
  
  // Get testcase requirements
  const getTestcaseRequirements = useCallback(async (testcaseId: string): Promise<Requirement[]> => {
    try {
      const url = buildServerUrl(`/server/requirements/testcase/${testcaseId}/requirements`);
      const response = await fetch(url);
      
      const data = await response.json();
      
      if (data.success) {
        return data.requirements || [];
      } else {
        console.error('[@useRequirements] Error getting testcase requirements:', data.error);
        return [];
      }
    } catch (err) {
      console.error('[@useRequirements] Error getting testcase requirements:', err);
      return [];
    }
  }, []);
  
  // Get script requirements
  const getScriptRequirements = useCallback(async (scriptName: string): Promise<Requirement[]> => {
    try {
      const url = buildServerUrl(`/server/requirements/script/${scriptName}/requirements`);
      const response = await fetch(url);
      
      const data = await response.json();
      
      if (data.success) {
        return data.requirements || [];
      } else {
        console.error('[@useRequirements] Error getting script requirements:', data.error);
        return [];
      }
    } catch (err) {
      console.error('[@useRequirements] Error getting script requirements:', err);
      return [];
    }
  }, []);
  
  // Load requirements on mount
  useEffect(() => {
    loadRequirements();
  }, [loadRequirements]);
  
  return {
    requirements,
    isLoading,
    error,
    createRequirement,
    updateRequirement,
    deleteRequirement,
    getRequirement,
    getRequirementByCode,
    loadRequirements,
    refreshRequirements,
    filters,
    setFilters,
    categories,
    priorities,
    appTypes,
    deviceModels,
    linkTestcase,
    unlinkTestcase,
    linkScript,
    unlinkScript,
    getTestcaseRequirements,
    getScriptRequirements,
  };
};

