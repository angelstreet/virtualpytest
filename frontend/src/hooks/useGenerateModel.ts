import { useState, useEffect, useCallback } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';
import type { ExplorationContext, ExplorationPhase, ExplorationStrategy } from '../types/exploration';

interface UseGenerateModelProps {
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  isControlActive: boolean;
  userinterfaceName?: string;
  onStructureCreated?: (nodesCount: number, edgesCount: number) => void;
  onClose?: () => void;
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

interface ValidationResult {
  step: number;
  itemName: string;
  nodeName: string;
  forward: {
    action: string;
    result: 'success' | 'failure';
    message: string;
  };
  reverse: {
    action: string;
    result: 'success' | 'failure' | 'skipped' | 'warning';
    message: string;
  };
  status: 'completed' | 'failed';
}

export const useGenerateModel = ({
  treeId,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  userinterfaceName,
  onStructureCreated,
  onClose
}: UseGenerateModelProps) => {
  // State
  const [explorationId, setExplorationId] = useState<string | null>(null);
  const [explorationHostName, setExplorationHostName] = useState<string | null>(null);
  const [isExploring, setIsExploring] = useState(false);
  const [status, setStatus] = useState<'idle' | 'exploring' | 'awaiting_approval' | 'structure_created' | 'awaiting_validation' | 'validating' | 'validation_complete' | 'completed' | 'failed'>('idle');
  const [phase, setPhase] = useState<'analysis' | 'structure' | 'validation' | null>(null);
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
    reasoning: '',
    screenshot: undefined
  });
  const [explorationPlan, setExplorationPlan] = useState<ExplorationPlan | null>(null);
  
  // ✅ Selected nodes state (all selected by default)
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const [proposedNodes, setProposedNodes] = useState<ProposedNode[]>([]);
  const [proposedEdges, setProposedEdges] = useState<ProposedEdge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [validationProgress, setValidationProgress] = useState<{current: number, total: number}>({current: 0, total: 0});
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  
  // ✅ NEW v2.0: Context and phase state
  const [context, setContext] = useState<ExplorationContext | null>(null);
  const [currentPhase, setCurrentPhase] = useState<ExplorationPhase | null>(null);
  const [strategy, setStrategy] = useState<ExplorationStrategy | null>(null);
  
  // ✅ Auto-select all nodes when context.predicted_items is available
  useEffect(() => {
    if (context?.predicted_items && context.predicted_items.length > 0) {
      setSelectedNodes(new Set(context.predicted_items));
    }
  }, [context?.predicted_items]);
  
  // ✅ Toggle node selection
  const toggleNodeSelection = useCallback((nodeName: string) => {
    setSelectedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeName)) {
        newSet.delete(nodeName);
      } else {
        newSet.add(nodeName);
      }
      return newSet;
    });
  }, []);

  // Clear state when dependencies change
  useEffect(() => {
    if (!isControlActive) {
      resetState();
    }
  }, [isControlActive, treeId, selectedHost, selectedDeviceId]);

  const resetState = useCallback(() => {
    console.log('[@useGenerateModel:resetState] 🔴 RESETTING ALL HOOK STATE');
    console.trace('[@useGenerateModel:resetState] Call stack:');
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
      reasoning: '',
      screenshot: undefined
    });
    setExplorationPlan(null);
    setProposedNodes([]);
    setProposedEdges([]);
    setError(null);
    setIsGenerating(false);
    setValidationProgress({current: 0, total: 0});
    setValidationResults([]);
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

  // Polling effect - polls every 5 seconds when exploring
  useEffect(() => {
    console.log('[@useGenerateModel:pollingEffect] Triggered', {
      isExploring,
      explorationId,
      explorationHostName,
      willStartPolling: isExploring && explorationId && explorationHostName
    });
    
    if (isExploring && explorationId && explorationHostName) {
      console.log('[@useGenerateModel:pollingEffect] ✅ Starting polling interval (5s)');
      const interval = setInterval(() => {
        console.log('[@useGenerateModel:pollingEffect] ⏰ Interval fired - calling fetchExplorationStatus');
        fetchExplorationStatus();
      }, 5000);
      
      return () => {
        console.log('[@useGenerateModel:pollingEffect] 🧹 Cleanup - clearing interval');
        clearInterval(interval);
      };
    } else {
      console.log('[@useGenerateModel:pollingEffect] ❌ NOT starting polling - conditions not met');
    }
  }, [isExploring, explorationId, explorationHostName, fetchExplorationStatus]);

  const startExploration = useCallback(async () => {
    if (!treeId || !selectedHost || !selectedDeviceId || !isControlActive) {
      setError('Missing required parameters for exploration');
      return;
    }

    try {
      setError(null);
      setIsExploring(true);
      setStatus('exploring');
      setCurrentStep('Cleaning up previous _temp nodes...');
      
      console.log('[@useGenerateModel:startExploration] Cleaning up _temp nodes before starting');
      
      // ✅ STEP 1: Clean up any existing _temp nodes/edges
      try {
        const cleanupResponse = await fetch(buildServerUrl('/server/ai-generation/cleanup-temp'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tree_id: treeId,
            host_name: selectedHost.host_name
          })
        });
        
        if (cleanupResponse.ok) {
          const cleanupData = await cleanupResponse.json();
          console.log('[@useGenerateModel:startExploration] Cleanup complete:', cleanupData);
        } else {
          console.warn('[@useGenerateModel:startExploration] Cleanup failed, continuing anyway');
        }
      } catch (cleanupErr) {
        console.warn('[@useGenerateModel:startExploration] Cleanup error, continuing anyway:', cleanupErr);
      }
      
      setCurrentStep('Starting AI exploration (2-level depth)...');
      
      console.log('[@useGenerateModel:startExploration] Starting exploration with params:', {
        treeId,
        host_name: selectedHost.host_name,
        device_id: selectedDeviceId,
        userinterface_name: userinterfaceName
      });

      // ✅ STEP 2: Start new exploration (depth is fixed at 2 levels)
      const response = await fetch(buildServerUrl('/server/ai-generation/start-exploration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: treeId,
          host_name: selectedHost.host_name,  // ← Just the name!
          device_id: selectedDeviceId,
          userinterface_name: userinterfaceName
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
        console.log('[@useGenerateModel:startExploration] 🔍 DEBUG - explorationHostName set to:', data.host_name);
        console.log('[@useGenerateModel:startExploration] 🔍 DEBUG - isExploring:', true);
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
      setPhase('structure');
      setCurrentStep('Creating navigation structure...');
      
      console.log('[@useGenerateModel:continueExploration] Creating structure (Phase 2a):', explorationId);

      const response = await fetch(buildServerUrl(`/server/ai-generation/continue-exploration?host_name=${encodeURIComponent(explorationHostName)}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        // Structure created - update status
        setStatus('structure_created');
        setPhase('structure');
        setCurrentStep(`Created ${data.nodes_created} nodes and ${data.edges_created} edges. Ready to validate.`);
        setIsExploring(false);
        console.log('[@useGenerateModel:continueExploration] ✅ Structure created:', data);
        console.log('[@useGenerateModel:continueExploration] Current state:', {
          explorationId,
          status: 'structure_created',
          phase: 'structure'
        });
        
        // ✅ Close modal and notify parent
        if (onClose) {
          console.log('[@useGenerateModel:continueExploration] 🚪 Calling onClose() - modal will close');
          onClose();
        }
        
        // ✅ Trigger structure created callback (will show ValidationReadyPrompt)
        if (onStructureCreated) {
          console.log('[@useGenerateModel:continueExploration] 📢 Calling onStructureCreated callback');
          onStructureCreated(data.nodes_created, data.edges_created);
        }
      } else {
        throw new Error(data.error || 'Failed to create structure');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:continueExploration] Error:', err);
      setError(err.message || 'Failed to create structure');
      setIsExploring(false);
      setStatus('failed');
    }
  }, [explorationId, explorationHostName]);
  
  const startValidation = useCallback(async () => {
    if (!explorationId || !explorationHostName) {
      setError('No exploration session found');
      return;
    }

    try {
      setError(null);
      setStatus('awaiting_validation');
      setPhase('validation');
      setCurrentStep('Starting validation...');
      
      console.log('[@useGenerateModel:startValidation] Starting validation (Phase 2b)');

      const response = await fetch(buildServerUrl(`/server/ai-generation/start-validation?host_name=${encodeURIComponent(explorationHostName)}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setValidationProgress({current: 0, total: data.total_items});
        console.log('[@useGenerateModel:startValidation] Validation ready:', data);
      } else {
        throw new Error(data.error || 'Failed to start validation');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:startValidation] Error:', err);
      setError(err.message || 'Failed to start validation');
      setStatus('failed');
    }
  }, [explorationId, explorationHostName]);
  
  const validateNextItem = useCallback(async () => {
    if (!explorationId || !explorationHostName) {
      setError('No exploration session found');
      return null;
    }

    try {
      setError(null);
      setStatus('validating');
      
      console.log('[@useGenerateModel:validateNextItem] Validating next item');

      const response = await fetch(buildServerUrl(`/server/ai-generation/validate-next-item?host_name=${encodeURIComponent(explorationHostName)}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        console.log('[@useGenerateModel:validateNextItem] Item validated:', data);
        
        // Collect validation result
        if (data.progress && data.action_sets) {
          const stepResult: ValidationResult = {
            step: data.progress.current_item,
            itemName: data.item,
            nodeName: data.node_name,
            forward: {
              action: data.action_sets.forward.action,
              result: data.click_result === 'success' ? 'success' : 'failure',
              message: data.click_result || 'Element not found'
            },
            reverse: {
              action: data.action_sets.reverse.action,
              result: data.back_result === 'success' ? 'success' : 
                     data.back_result && data.back_result.includes('wait_for_element_by_text') ? 'warning' :
                     data.click_result !== 'success' ? 'skipped' : 'failure',
              message: data.back_result || 'Verification failed'
            },
            status: data.click_result === 'success' ? 'completed' : 'failed'
          };
          
          setValidationResults(prev => [...prev, stepResult]);
          
          // Update validation progress with detailed action set info
          setValidationProgress({
            current: data.progress.current_item,
            total: data.progress.total_items
          });
          
          // Build detailed step message showing both action sets
          const forwardStatus = data.action_sets.forward.result === 'success' ? '✅' : '❌';
          const reverseStatus = data.action_sets.reverse.result === 'success' ? '✅' : '❌';
          
          setCurrentStep(
            `Item ${data.progress.current_item}/${data.progress.total_items}: ${data.node_name}\n` +
            `${forwardStatus} 1. ${data.action_sets.forward.source} → ${data.action_sets.forward.target}: ${data.action_sets.forward.action}\n` +
            `${reverseStatus} 2. ${data.action_sets.reverse.source} → ${data.action_sets.reverse.target}: ${data.action_sets.reverse.action}`
          );
        }
        
        // Update status based on whether more items remain
        if (data.has_more_items) {
          // ✅ STAY in 'validating' status - don't reset to 'awaiting_validation'
          // The modal's handleValidateNext() will continue the loop
          // Status stays 'validating' to keep progress visible
        } else {
          setStatus('validation_complete');
          setIsExploring(false);
          setCurrentStep('All action sets validated - ready to finalize');
        }
        
        return data; // Return validation results
      } else {
        throw new Error(data.error || 'Failed to validate item');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:validateNextItem] Error:', err);
      setError(err.message || 'Failed to validate item');
      setStatus('awaiting_validation'); // Allow retry
      return null;
    }
  }, [explorationId, explorationHostName]);

  const cancelExploration = useCallback(async () => {
    if (!explorationId || !selectedHost) return;

    try {
      console.log('[@useGenerateModel:cancelExploration] Cancelling exploration:', explorationId);
      
      // Cancel the exploration session
      await fetch(buildServerUrl(`/server/ai-generation/cancel-exploration?host_name=${encodeURIComponent(selectedHost.host_name)}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId
        })
      });

      // NOTE: Cleanup of _temp nodes is now handled by the parent component via onCleanupTemp callback
      
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

      const response = await fetch(buildServerUrl(`/server/ai-generation/approve-generation?host_name=${encodeURIComponent(selectedHost.host_name)}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploration_id: explorationId,
          tree_id: treeId,
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

  // ========== NEW v2.0: MCP-FIRST METHODS ==========
  
  /**
   * Phase 0: Detect device strategy
   */
  const executePhase0 = useCallback(async () => {
    if (!explorationHostName) {
      setError('No exploration host');
      return null;
    }

    try {
      setCurrentPhase('phase0');
      setCurrentStep('Detecting device strategy...');
      setIsExploring(true);

      const url = buildServerUrl(
        `/host/ai-generation/init?host_name=${encodeURIComponent(explorationHostName)}&team_id=${selectedHost?.team_id || ''}`
      );

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedDeviceId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setContext(data.context);
        setStrategy(data.strategy);
        console.log('[@useGenerateModel:executePhase0] Strategy detected:', data.strategy);
        return data;
      } else {
        throw new Error(data.error || 'Failed to detect strategy');
      }
    } catch (err: any) {
      console.error('[@useGenerateModel:executePhase0] Error:', err);
      setError(err.message || 'Failed to detect strategy');
      return null;
    } finally {
      setIsExploring(false);
    }
  }, [explorationHostName, selectedDeviceId, selectedHost?.team_id]);

  /**
   * Phase 2: Create and test items incrementally
   */
  const executePhase2Incremental = useCallback(async () => {
    if (!explorationHostName || !context) {
      setError('No exploration context');
      return null;
    }

    try {
      setCurrentPhase('phase2');
      setIsExploring(true);
      const results: any[] = [];

      // Loop until all items are processed or error occurs
      while (true) {
        setCurrentStep(`Creating item ${(context.current_step || 0) + 1}/${context.total_steps || 0}...`);

        const url = buildServerUrl(
          `/host/ai-generation/next?host_name=${encodeURIComponent(explorationHostName)}&team_id=${selectedHost?.team_id || ''}`
        );

        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_id: selectedDeviceId
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        results.push(data);

        if (!data.success) {
          // Stop on error
          setError(`Failed on item "${data.item}": ${data.error}`);
          setStatus('failed');
          break;
        }

        // Update context
        if (data.context) {
          setContext(data.context);
        }

        console.log(`[@useGenerateModel:executePhase2Incremental] Item "${data.item}" created and tested ✅`);

        if (!data.has_more_items) {
          // All items completed
          console.log('[@useGenerateModel:executePhase2Incremental] All items completed!');
          setStatus('structure_created');
          break;
        }
      }

      return results;
    } catch (err: any) {
      console.error('[@useGenerateModel:executePhase2Incremental] Error:', err);
      setError(err.message || 'Failed during incremental creation');
      setStatus('failed');
      return null;
    } finally {
      setIsExploring(false);
    }
  }, [explorationHostName, context, selectedDeviceId, selectedHost?.team_id]);

  return {
    // State
    explorationId,
    explorationHostName,
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
    validationProgress,
    validationResults,
    
    // ✅ NEW v2.0: Context and phase
    context,
    currentPhase,
    strategy,
    
    // ✅ Node selection
    selectedNodes,
    toggleNodeSelection,
    
    // Actions
    startExploration,
    continueExploration,
    startValidation,
    validateNextItem,
    cancelExploration,
    approveGeneration,
    resetState,
    
    // ✅ NEW v2.0: Phase methods
    executePhase0,
    executePhase2Incremental,
    
    // Computed
    canStart: !isExploring && !isGenerating && isControlActive && treeId && selectedHost && selectedDeviceId,
    hasResults: status === 'completed' && (proposedNodes.length > 0 || proposedEdges.length > 0),
    isAwaitingApproval: status === 'awaiting_approval',
    isStructureCreated: status === 'structure_created',
    isAwaitingValidation: status === 'awaiting_validation',
    isValidating: status === 'validating',
    isValidationComplete: status === 'validation_complete'
  };
};
