import { useState, useEffect, useCallback } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface UseGenerateModelProps {
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  isControlActive: boolean;
  userinterfaceName?: string;
}

interface Progress {
  total_screens_found: number;
  screens_analyzed: number;
  nodes_proposed: number;
  edges_proposed: number;
}

interface CurrentAnalysis {
  screen_name: string;
  elements_found: string[];
  reasoning: string;
  screenshot?: string;
}

interface ExplorationPlan {
  menu_type: string;
  items: string[];
  lines?: string[][];  // NEW: Line structure from AI
  strategy: string;
  predicted_depth: number;
  reasoning: string;
  screenshot?: string;
  screen_name: string;
}

interface ProposedNode {
  id: string;
  name: string;
  screen_type: string;
  reasoning: string;
  created_at?: number;
}

interface ProposedEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  data: any;
  reasoning: string;
  created_at?: number;
}

export const useGenerateModel = ({
  treeId,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  userinterfaceName
}: UseGenerateModelProps) => {
  // State
  const [explorationId, setExplorationId] = useState<string | null>(null);
  const [explorationHostName, setExplorationHostName] = useState<string | null>(null);
  const [isExploring, setIsExploring] = useState(false);
  const [status, setStatus] = useState<'idle' | 'exploring' | 'awaiting_approval' | 'completed' | 'failed'>('idle');
  const [phase, setPhase] = useState<'analysis' | 'exploration' | null>(null);
  const [currentStep, setCurrentStep] = useState('');
  const [progress, setProgress] = useState<Progress>({
    total_screens_found: 0,
    screens_analyzed: 0,
    nodes_proposed: 0,
    edges_proposed: 0
  });
  const [currentAnalysis, setCurrentAnalysis] = useState<CurrentAnalysis>({
    screen_name: '',
    elements_found: [],
    reasoning: ''
  });
  const [explorationPlan, setExplorationPlan] = useState<ExplorationPlan | null>(null);
  const [proposedNodes, setProposedNodes] = useState<ProposedNode[]>([]);
  const [proposedEdges, setProposedEdges] = useState<ProposedEdge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Clear state when dependencies change
  useEffect(() => {
    if (!isControlActive) {
      resetState();
    }
  }, [isControlActive, treeId, selectedHost, selectedDeviceId]);

  // Polling effect - polls every 5 seconds when exploring
  useEffect(() => {
    if (isExploring && explorationId && selectedHost) {
      const interval = setInterval(() => {
        fetchExplorationStatus();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [isExploring, explorationId, selectedHost]);

  const resetState = useCallback(() => {
    setExplorationId(null);
    setExplorationHostName(null);
    setIsExploring(false);
    setStatus('idle');
    setPhase(null);
    setCurrentStep('');
    setProgress({
      total_screens_found: 0,
      screens_analyzed: 0,
      nodes_proposed: 0,
      edges_proposed: 0
    });
    setCurrentAnalysis({
      screen_name: '',
      elements_found: [],
      reasoning: ''
    });
    setExplorationPlan(null);
    setProposedNodes([]);
    setProposedEdges([]);
    setError(null);
    setIsGenerating(false);
  }, []);

  const fetchExplorationStatus = useCallback(async () => {
    if (!explorationId || !explorationHostName) return;

    try {
      const response = await fetch(
        buildServerUrl(`/server/ai-generation/exploration-status/${explorationId}?host_name=${encodeURIComponent(explorationHostName)}`)
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setStatus(data.status);
        setPhase(data.phase);
        setCurrentStep(data.current_step || '');
        setProgress(data.progress || progress);
        setCurrentAnalysis(data.current_analysis || currentAnalysis);
        
        // If awaiting approval, show the plan and stop polling
        if (data.status === 'awaiting_approval') {
          setExplorationPlan(data.exploration_plan || null);
          setIsExploring(false);  // Stop polling
        }
        
        // If completed, set proposed nodes and edges
        if (data.status === 'completed') {
          setProposedNodes(data.proposed_nodes || []);
          setProposedEdges(data.proposed_edges || []);
          setIsExploring(false);
        }
        
        // If failed, set error
        if (data.status === 'failed') {
          setError(data.error || 'Exploration failed');
          setIsExploring(false);
        }
      } else {
        setError(data.error || 'Failed to get exploration status');
        setIsExploring(false);
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:fetchExplorationStatus] Error:', err);
      setError(err.message || 'Failed to fetch exploration status');
      setIsExploring(false);
    }
  }, [explorationId, explorationHostName, progress, currentAnalysis]);

  const startExploration = useCallback(async (depth: number = 5) => {
    if (!treeId || !selectedHost || !selectedDeviceId || !isControlActive) {
      setError('Missing required parameters for exploration');
      return;
    }

    try {
      setError(null);
      setIsExploring(true);
      setStatus('exploring');
      setCurrentStep('Starting AI exploration...');
      
      console.log('[@useGenerateModel:startExploration] Starting exploration with params:', {
        treeId,
        host_name: selectedHost.host_name,
        device_id: selectedDeviceId,
        userinterface_name: userinterfaceName,
        exploration_depth: depth
      });

      const response = await fetch(buildServerUrl('/server/ai-generation/start-exploration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: treeId,
          host_name: selectedHost.host_name,  // ← Just the name!
          device_id: selectedDeviceId,
          userinterface_name: userinterfaceName,
          exploration_depth: depth
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setExplorationId(data.exploration_id);
        setExplorationHostName(data.host_name); // Store host_name from response
        setCurrentStep('Exploration started successfully');
        console.log('[@useGenerateModel:startExploration] Exploration started:', data.exploration_id);
      } else {
        throw new Error(data.error || 'Failed to start exploration');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:startExploration] Error:', err);
      setError(err.message || 'Failed to start exploration');
      setIsExploring(false);
      setStatus('failed');
    }
  }, [treeId, selectedHost, selectedDeviceId, isControlActive, userinterfaceName]);

  const continueExploration = useCallback(async () => {
    if (!explorationId || !explorationHostName) {
      setError('No exploration session to continue');
      return;
    }

    try {
      setError(null);
      setIsExploring(true);
      setStatus('exploring');
      setPhase('exploration');
      setCurrentStep('Starting Phase 2: Exploring navigation tree...');
      
      console.log('[@useGenerateModel:continueExploration] Continuing to Phase 2:', explorationId);

      const response = await fetch(buildServerUrl('/server/ai-generation/continue-exploration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId,
          host_name: explorationHostName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        // Initialize incremental exploration
        setStatus('awaiting_item_approval');
        setCurrentStep(`Ready to explore items (${data.total_items} total)`);
        console.log('[@useGenerateModel:continueExploration] Phase 2 initialized:', data);
      } else {
        throw new Error(data.error || 'Failed to continue exploration');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:continueExploration] Error:', err);
      setError(err.message || 'Failed to continue exploration');
      setIsExploring(false);
      setStatus('failed');
    }
  }, [explorationId, explorationHostName]);
  
  const exploreNextItem = useCallback(async () => {
    if (!explorationId || !explorationHostName) {
      setError('No exploration session found');
      return null;
    }

    try {
      setError(null);
      setStatus('exploring_item');
      
      console.log('[@useGenerateModel:exploreNextItem] Exploring next item');

      const response = await fetch(buildServerUrl('/server/ai-generation/explore-next-item'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId,
          host_name: explorationHostName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        console.log('[@useGenerateModel:exploreNextItem] Item explored:', data);
        
        // Update status based on whether more items remain
        if (data.has_more_items) {
          setStatus('awaiting_item_approval');
          setCurrentStep(`Explored item ${data.progress.current_item}/${data.progress.total_items}`);
        } else {
          setStatus('completed');
          setIsExploring(false);
          setCurrentStep('All items explored - ready for final approval');
        }
        
        return data; // Return node/edge data for ReactFlow update
      } else {
        throw new Error(data.error || 'Failed to explore item');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:exploreNextItem] Error:', err);
      setError(err.message || 'Failed to explore item');
      setStatus('awaiting_item_approval'); // Allow retry
      return null;
    }
  }, [explorationId, explorationHostName]);

  const cancelExploration = useCallback(async () => {
    if (!explorationId || !selectedHost) return;

    try {
      console.log('[@useGenerateModel:cancelExploration] Cancelling exploration:', explorationId);
      
      await fetch(buildServerUrl('/server/ai-generation/cancel-exploration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId,
          host_ip: selectedHost.host_ip
        })
      });

      resetState();
    } catch (err: any) {
      console.error('[@useGenerateModel:cancelExploration] Error:', err);
      setError(err.message || 'Failed to cancel exploration');
    }
  }, [explorationId, selectedHost, resetState]);

  const approveGeneration = useCallback(async (nodeIds: string[], edgeIds: string[]) => {
    if (!explorationId || !treeId || !selectedHost) {
      setError('Missing required parameters for generation');
      return;
    }

    try {
      setIsGenerating(true);
      setError(null);
      
      console.log('[@useGenerateModel:approveGeneration] Approving generation:', {
        nodeIds,
        edgeIds,
        explorationId,
        treeId
      });

      const response = await fetch(buildServerUrl('/server/ai-generation/approve-generation'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId,
          tree_id: treeId,
          host_ip: selectedHost.host_ip,
          approved_nodes: nodeIds,
          approved_edges: edgeIds
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        console.log('[@useGenerateModel:approveGeneration] Generation completed:', {
          nodes_created: data.nodes_created,
          edges_created: data.edges_created
        });
        
        // Reset state after successful generation
        resetState();
        return data;
      } else {
        throw new Error(data.error || 'Failed to approve generation');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:approveGeneration] Error:', err);
      setError(err.message || 'Failed to approve generation');
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, [explorationId, treeId, selectedHost, resetState]);

  return {
    // State
    explorationId,
    isExploring,
    status,
    phase,
    currentStep,
    progress,
    currentAnalysis,
    explorationPlan,
    proposedNodes,
    proposedEdges,
    error,
    isGenerating,
    
    // Actions
    startExploration,
    continueExploration,
    exploreNextItem,
    cancelExploration,
    approveGeneration,
    resetState,
    
    // Computed
    canStart: !isExploring && !isGenerating && isControlActive && treeId && selectedHost && selectedDeviceId,
    hasResults: status === 'completed' && (proposedNodes.length > 0 || proposedEdges.length > 0),
    isAwaitingApproval: status === 'awaiting_approval',
    isAwaitingItemApproval: status === 'awaiting_item_approval'
  };
};
