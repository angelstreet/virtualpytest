import { useState, useCallback, useEffect, useRef } from 'react';
import { buildSelectedServerUrl } from '../../utils/buildUrlUtils';
import { useServerManager } from '../useServerManager';
import { TestCase, Campaign, Tree } from '../../types';
import { DashboardStats, RecentActivity } from '../../types/pages/Dashboard_Types';

export interface UseDashboardReturn {
  // Data
  stats: DashboardStats;
  
  // Loading states
  loading: boolean;
  error: string | null;
  isRequestInProgress: boolean;
  
  // Actions
  refreshData: () => Promise<void>;
}

export const useDashboard = (): UseDashboardReturn => {
  const { selectedServer } = useServerManager();
  const [stats, setStats] = useState<DashboardStats>({
    testCases: 0,
    campaigns: 0,
    trees: 0,
    recentActivity: [],
  });
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRequestInProgress, setIsRequestInProgress] = useState(false);
  
  // Use ref to track the current selectedServer to avoid dependency issues
  const selectedServerRef = useRef(selectedServer);
  selectedServerRef.current = selectedServer;
  
  // Debug: Log when selectedServer changes
  useEffect(() => {
    console.log('[@useDashboard] selectedServer changed to:', selectedServer);
  }, [selectedServer]);

  const fetchDashboardData = useCallback(async () => {
    // Prevent duplicate calls
    if (isRequestInProgress) {
      console.log('[@useDashboard] Request already in progress, skipping duplicate call');
      return;
    }
    
    try {
      setIsRequestInProgress(true);
      setLoading(true);
      setError(null);
      
      // Don't proceed if no selected server yet
      if (!selectedServerRef.current) {
        console.log('[@useDashboard] No selected server yet, skipping fetch');
        setLoading(false);
        setIsRequestInProgress(false);
        return;
      }
      
      // Fetch campaigns, testcases, trees using selected server
      const [campaignsResponse, testCasesResponse, treesResponse] = await Promise.all([
        fetch(buildSelectedServerUrl('/server/campaigns/getAllCampaigns', selectedServerRef.current)),
        fetch(buildSelectedServerUrl('/server/testcases/getAllTestCases', selectedServerRef.current)),
        fetch(buildSelectedServerUrl('/server/navigationTrees', selectedServerRef.current)), // Automatically includes team_id
      ]);

      let testCases: TestCase[] = [];
      let campaigns: Campaign[] = [];
      let trees: Tree[] = [];

      if (testCasesResponse.ok) {
        testCases = await testCasesResponse.json();
      }

      if (campaignsResponse.ok) {
        campaigns = await campaignsResponse.json();
      }

      if (treesResponse.ok) {
        const treesData = await treesResponse.json();
        // The navigation API returns { success: true, trees: [...] }
        if (treesData.success && treesData.trees) {
          trees = treesData.trees;
        }
      }

      // Generate mock recent activity with proper RecentActivity type
      const recentActivity: RecentActivity[] = [
        ...testCases.slice(0, 3).map(
          (tc): RecentActivity => ({
            id: tc.test_id,
            type: 'test' as const,
            name: tc.name,
            status: 'success' as const,
            timestamp: new Date().toISOString(),
          }),
        ),
        ...campaigns.slice(0, 2).map(
          (c): RecentActivity => ({
            id: c.campaign_id,
            type: 'campaign' as const,
            name: c.name,
            status: 'pending' as const,
            timestamp: new Date().toISOString(),
          }),
        ),
      ].slice(0, 5);

      setStats({
        testCases: testCases.length,
        campaigns: campaigns.length,
        trees: trees.length,
        recentActivity,
      });
      
    } catch (err) {
      setError('Failed to fetch dashboard data');
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
      setIsRequestInProgress(false);
    }
  }, [isRequestInProgress]);

  const refreshData = useCallback(async () => {
    await fetchDashboardData();
  }, []);

  // Load data on mount and when selectedServer changes
  useEffect(() => {
    if (selectedServer) {
      console.log('[@useDashboard] Selected server changed, refreshing data...');
      fetchDashboardData();
    }
  }, [selectedServer]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Data
    stats,
    
    // Loading states
    loading,
    error,
    isRequestInProgress,
    
    // Actions
    refreshData,
  };
};

