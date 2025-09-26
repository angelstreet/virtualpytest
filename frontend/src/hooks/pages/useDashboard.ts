import { useState, useCallback, useEffect } from 'react';
import { buildServerUrl, getAllServerUrls, buildServerUrlForServer } from '../../utils/buildUrlUtils';
import { TestCase, Campaign, Tree } from '../../types';
import { Host } from '../../types/common/Host_Types';
import { DashboardStats, RecentActivity } from '../../types/pages/Dashboard_Types';

export interface ServerHostData {
  server_info: { 
    server_name: string; 
    server_url: string; 
    server_port: string; 
  };
  hosts: Host[];
}

export interface UseDashboardReturn {
  // Data
  stats: DashboardStats;
  serverHostsData: ServerHostData[];
  
  // Loading states
  loading: boolean;
  error: string | null;
  isRequestInProgress: boolean;
  
  // Actions
  fetchDashboardData: () => Promise<void>;
  refreshData: () => Promise<void>;
}

export const useDashboard = (): UseDashboardReturn => {
  const [stats, setStats] = useState<DashboardStats>({
    testCases: 0,
    campaigns: 0,
    trees: 0,
    recentActivity: [],
  });
  
  const [serverHostsData, setServerHostsData] = useState<ServerHostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRequestInProgress, setIsRequestInProgress] = useState(false);

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
      
      // Get all configured server URLs
      const serverUrls = getAllServerUrls();
      
      // Fetch from all servers in parallel
      const serverDataPromises = serverUrls.map(async (serverUrl) => {
        try {
          const response = await fetch(buildServerUrlForServer(serverUrl, '/server/system/getAllHosts'));
          if (response.ok) {
            const data = await response.json();
            return {
              server_info: data.server_info || {
                server_name: `Server (${serverUrl})`,
                server_url: serverUrl,
                server_port: serverUrl.split(':').pop()
              },
              hosts: data.hosts || []
            };
          }
        } catch (error) {
          console.error(`Failed to fetch from ${serverUrl}:`, error);
        }
        return null;
      });
      
      const serverHostsData = (await Promise.all(serverDataPromises)).filter(Boolean) as ServerHostData[];
      setServerHostsData(serverHostsData);
      
      // Continue with existing logic for campaigns, testcases, trees using primary server
      const [campaignsResponse, testCasesResponse, treesResponse] = await Promise.all([
        fetch(buildServerUrl('/server/campaigns/getAllCampaigns')),
        fetch(buildServerUrl('/server/testcases/getAllTestCases')),
        fetch(buildServerUrl('/server/navigationTrees')), // Automatically includes team_id
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
  }, [fetchDashboardData]);

  useEffect(() => {
    fetchDashboardData();
    // Load data once on mount only - no polling needed
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Data
    stats,
    serverHostsData,
    
    // Loading states
    loading,
    error,
    isRequestInProgress,
    
    // Actions
    fetchDashboardData,
    refreshData,
  };
};
