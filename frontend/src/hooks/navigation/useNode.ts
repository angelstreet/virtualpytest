import { useCallback, useState, useEffect, useMemo, useRef } from 'react';

import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { Host } from '../../types/common/Host_Types';
import {
  UINavigationNode,
  NodeForm,
  NavigationStep,
  NavigationPreviewResponse,
} from '../../types/pages/Navigation_Types';
import { useValidationColors } from '../validation/useValidationColors';

import { buildServerUrl } from '../../utils/buildUrlUtils';
import { executeNavigationAsync } from '../../utils/navigationExecutionUtils';
export interface UseNodeProps {
  selectedHost?: Host;
  selectedDeviceId?: string;
  isControlActive?: boolean;
  treeId?: string;
  currentNodeId?: string;
}

export const useNode = (props?: UseNodeProps) => {
  // Debug logging removed - was causing noise on every re-render
  
  const { getModelReferences, referencesLoading, currentDeviceId } = useDeviceData();
  const { currentNodeId, updateCurrentPosition, updateNodesWithMinimapIndicators, nodes, parentChain, userInterface } =
    useNavigation();
  const {
    setNavigationEdgesSuccess,
    setNavigationEdgesFailure,
    resetNavigationEdgeColors,
    setNodeVerificationSuccess,
    setNodeVerificationFailure,
    resetNodeVerificationColors,
  } = useValidationColors();
  const navigationConfig = useNavigationConfig();

  // Create a ref for the navigation callback to avoid circular dependency
  const navigationCallbackRef = useRef<((nodeId: string) => void) | undefined>();

  // Timer actions should only be used during actual action execution, not general navigation
  // This will be moved to action execution contexts where it's actually needed

  // Get the selected device from the host's devices array
  const selectedDevice = useMemo(() => {
    return props?.selectedHost?.devices?.find(
      (device) => device.device_id === props?.selectedDeviceId,
    );
  }, [props?.selectedHost, props?.selectedDeviceId]);

  // Get the device model from the selected device
  const deviceModel = selectedDevice?.device_model;

  // Get model references using the device model
  const modelReferences = useMemo(() => {
    if (!deviceModel) {
      return {};
    }
    return getModelReferences(deviceModel);
  }, [getModelReferences, deviceModel]);

  // State for screenshot operations
  const [screenshotSaveStatus, setScreenshotSaveStatus] = useState<'idle' | 'success' | 'error'>(
    'idle',
  );

  // Navigation state for NodeGotoPanel
  const [navigationTransitions, setNavigationTransitions] = useState<NavigationStep[]>([]);
  const [isLoadingPreview, setIsLoadingPreview] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const [debugReportUrl, setDebugReportUrl] = useState<string | null>(null);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);

  /**
   * Get node form data with verifications (already resolved by NavigationConfigContext)
   */
  const getNodeFormWithVerifications = useCallback((node: UINavigationNode): NodeForm => {
    return {
      label: node.data.label,
      type: node.type as 'screen' | 'menu' | 'action' | 'entry',
      description: node.data.description || '',
      screenshot: node.data.screenshot,
      depth: node.data.depth || 0,
      parent: node.data.parent || [],
      menu_type: node.data.menu_type,
      priority: node.data.priority || 'p3', // Default to p3 if not set
      verifications: node.data.verifications || [], // Embedded verifications - no ID resolution needed
      verification_pass_condition: node.data.verification_pass_condition || 'all', // Default to 'all' if not set
    };
  }, []);

  /**
   * Take and save screenshot for a node
   */
  const takeAndSaveScreenshot = useCallback(
    async (
      label: string,
      nodeId: string,
      onUpdateNode?: (nodeId: string, updatedData: any) => void,
      nodeType?: string,
    ) => {
      if (!props?.selectedHost || !props?.selectedDeviceId) {
        return { success: false, message: 'Host or device not available' };
      }

      // Prevent screenshots for action nodes
      if (nodeType === 'action') {
        return { success: false, message: 'Screenshots are not allowed for action nodes' };
      }

      // Get userinterface name from navigation context
      const userinterfaceName = userInterface?.name;
      
      if (!userinterfaceName) {
        return { success: false, message: 'User interface not available - cannot determine screenshot path' };
      }

      try {
        // Sanitize filename by removing spaces and special characters
        const sanitizedFilename = label.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
        
        const response = await fetch(buildServerUrl('/server/av/saveScreenshot'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host_name: props.selectedHost.host_name,
            device_id: props.selectedDeviceId,
            filename: sanitizedFilename,
            userinterface_name: userinterfaceName,
          }),
        });

        const result = await response.json();

        if (result.success) {
          if (onUpdateNode) {
            onUpdateNode(nodeId, {
              screenshot: result.screenshot_url,
              screenshot_timestamp: Date.now(), // ✅ Force cache bust on same URL
            });
          }
          return { success: true, screenshot_url: result.screenshot_url };
        } else {
          return { success: false, message: result.message };
        }
      } catch (error) {
        return {
          success: false,
          message: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    },
    [props?.selectedHost, props?.selectedDeviceId, userInterface],
  );

  /**
   * Handle screenshot confirmation and execution
   */
  const handleScreenshotConfirm = useCallback(
    async (
      selectedNode: UINavigationNode,
      onUpdateNode?: (nodeId: string, updatedData: any) => void,
    ) => {
      if (!props?.isControlActive || !props?.selectedHost || !props?.selectedDeviceId) {
        return;
      }

      const result = await takeAndSaveScreenshot(
        selectedNode.data.label,
        selectedNode.id,
        onUpdateNode,
        selectedNode.type,
      );

      if (result.success) {
        setScreenshotSaveStatus('success');
        setTimeout(() => setScreenshotSaveStatus('idle'), 3000);
      } else {
        setScreenshotSaveStatus('error');
        setTimeout(() => setScreenshotSaveStatus('idle'), 3000);
      }
    },
    [props?.isControlActive, props?.selectedHost, props?.selectedDeviceId, takeAndSaveScreenshot],
  );

  /**
   * Get parent names from parent IDs
   */
  const getParentNames = useCallback((parentIds: string[], nodes: UINavigationNode[]): string => {
    if (!parentIds || parentIds.length === 0) return 'None';
    if (!nodes || !Array.isArray(nodes)) return 'None';

    const parentNames = parentIds.map((id) => {
      const parentNode = nodes.find((node) => node.id === id);
      return parentNode ? parentNode.data.label : id;
    });

    return parentNames.join(' > ');
  }, []);

  /**
   * Get full path for navigation (NodeGotoPanel)
   * Shows the actual navigation path from current position, not hierarchical structure
   */
  const getFullPath = useCallback(
    (selectedNode: UINavigationNode, nodes: UINavigationNode[]): string => {
      // If we have navigation transitions, use them to show the actual path
      if (navigationTransitions && navigationTransitions.length > 0) {
        const pathSegments: string[] = [];

        // Add the starting position from the first transition
        const firstTransition = navigationTransitions[0] as any;
        if (firstTransition?.from_node_label) {
          pathSegments.push(firstTransition.from_node_label);
        }

        // Add each transition target
        navigationTransitions.forEach((transition: any) => {
          if (transition?.to_node_label) {
            pathSegments.push(transition.to_node_label);
          }
        });

        return pathSegments.join(' → ');
      }

      // If we have a current position, show current → target
      if (currentNodeId) {
        const currentNode = nodes.find((node) => node.id === currentNodeId);
        const currentLabel = currentNode?.data.label || 'Current';

        // If already at target, just show the target
        if (currentNodeId === selectedNode.id) {
          return selectedNode.data.label;
        }

        return `${currentLabel} → ${selectedNode.data.label}`;
      }

      // Fallback to hierarchical structure if no current position
      const parentNames = getParentNames(selectedNode.data.parent || [], nodes);
      if (parentNames === 'None') {
        return selectedNode.data.label;
      }
      return `${parentNames} → ${selectedNode.data.label}`;
    },
    [getParentNames, navigationTransitions, currentNodeId],
  );

  /**
   * Load navigation preview for NodeGotoPanel - ALWAYS fetch fresh data
   */
  const loadNavigationPreview = useCallback(
    async (
      selectedNode: UINavigationNode,
      _allNodes?: UINavigationNode[],
      shouldUpdateMinimap: boolean = false,
    ): Promise<NavigationStep[]> => {
      if (!props?.treeId) return [];

      // Check if target is an action node - action nodes are not navigatable destinations
      if (selectedNode.type === 'action') {
        setNavigationError('Cannot navigate to action nodes - they are operations, not destinations');
        return [];
      }

      // Use only context currentNodeId - no fallbacks
      const startingNodeId = currentNodeId;

      const pathfindingTreeId = parentChain[0]?.treeId || props.treeId;

      setIsLoadingPreview(true);
      setNavigationError(null);

      try {
        // Use buildServerUrl to ensure team_id is automatically included
        const baseUrl = buildServerUrl(`/server/navigation/preview/${pathfindingTreeId}/${selectedNode.id}`);
        const url = new URL(baseUrl);

        // Add required host_name parameter from props (same as execution)
        if (props.selectedHost?.host_name) {
          url.searchParams.append('host_name', props.selectedHost.host_name);
        }

        // Add device_id parameter from context (required for proper device routing)
        if (currentDeviceId) {
          url.searchParams.append('device_id', currentDeviceId);
        }

        // Only add current_node_id if we have a valid starting node
        if (startingNodeId) {
          url.searchParams.append('current_node_id', startingNodeId);
        }

        const response = await fetch(url.toString(), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const result: NavigationPreviewResponse = await response.json();

        if (result.success) {
          // Use the correct property name from server response
          const transitions = result.transitions || [];
          setNavigationTransitions(transitions);

          // Only update minimap indicators if explicitly requested (during execution)
          if (shouldUpdateMinimap) {
            updateNodesWithMinimapIndicators(transitions);
          }

          return transitions;
        } else {
          setNavigationError(result.error || 'Failed to load navigation preview');
          return [];
        }
      } catch (err) {
        setNavigationError(
          `Failed to load navigation preview: ${err instanceof Error ? err.message : 'Unknown error'}`,
        );
        return [];
      } finally {
        setIsLoadingPreview(false);
      }
    },
    [props?.treeId, props?.selectedHost, currentNodeId, updateNodesWithMinimapIndicators, parentChain],
  );

  /**
   * Execute navigation using centralized NavigationContext method
   */
  const executeNavigation = useCallback(
    async (selectedNode: UINavigationNode) => {
      if (!props?.treeId) return;

      // 🛡️ GUARD: Prevent execution if already executing
      if (isExecuting) {
        console.log('[@useNode:executeNavigation] Ignoring click - navigation already in progress');
        return;
      }

      // Check if target is an action node - action nodes are not navigatable destinations
      if (selectedNode.type === 'action') {
        setNavigationError('Cannot navigate to action nodes - they are operations, not destinations');
        return;
      }

      setIsExecuting(true);
      setNavigationError(null);

      // Reset edge colors to grey before starting new navigation
      resetNavigationEdgeColors();

      // Reset node verification colors before starting new navigation
      if (currentNodeId) {
        resetNodeVerificationColors(currentNodeId);
      }

      try {
        const executionTreeId = parentChain[0]?.treeId || navigationConfig.actualTreeId;
        
        if (!executionTreeId) {
          throw new Error('No tree ID available for navigation execution');
        }
        
        console.log('[@useNode:executeNavigation] 🎯 NAVIGATION EXECUTION REQUEST:');
        console.log('[@useNode:executeNavigation]   → Target Node ID:', selectedNode.id);
        console.log('[@useNode:executeNavigation]   → Target Node Label:', selectedNode.data.label);
        console.log('[@useNode:executeNavigation]   → Target Node Type:', selectedNode.type);
        console.log('[@useNode:executeNavigation]   → Execution Tree ID:', executionTreeId);
        console.log('[@useNode:executeNavigation]   → Current Node ID:', currentNodeId || 'None');
        console.log('[@useNode:executeNavigation]   → UserInterface Name:', userInterface?.name);
        console.log('[@useNode:executeNavigation]   → Host:', props.selectedHost?.host_name);
        console.log('[@useNode:executeNavigation]   → Device:', currentDeviceId);
        
        if (!props.selectedHost?.host_name) {
          throw new Error('Host name is required for navigation execution');
        }
        
        // ✅ REUSE: Use shared navigation execution utility
        const response = await executeNavigationAsync({
          treeId: executionTreeId,
          targetNodeId: selectedNode.id, // ✅ CORRECT: Use UUID as targetNodeId
          hostName: props.selectedHost.host_name,
          deviceId: props.selectedDeviceId || currentDeviceId || 'device1', // ✅ FIX: Use props.selectedDeviceId first
          userinterfaceName: userInterface?.name || '',
          currentNodeId: currentNodeId || undefined,
          onProgress: (message) => {
            setExecutionMessage(message);
          }
        });

        setExecutionMessage(`Navigation to ${selectedNode.data.label} completed successfully`);
        setIsExecuting(false);

        // Update current position using centralized method
        const finalPositionNodeId = response.final_position_node_id || selectedNode.id;
        updateCurrentPosition(finalPositionNodeId, selectedNode.data.label);

        // Handle verification results
        if (response.verification_results && response.verification_results.length > 0) {
          // ✅ FIX: Respect node's verification_pass_condition setting
          const passCondition = selectedNode.data.verification_pass_condition || 'all';
          const verificationSuccess = passCondition === 'any'
            ? response.verification_results.some((vr: any) => vr.success)  // At least one must pass
            : response.verification_results.every((vr: any) => vr.success); // All must pass
          
          console.log(`[@useNode:executeNavigation] Verification pass condition: ${passCondition}`);
          console.log(`[@useNode:executeNavigation] Verification results: ${response.verification_results.filter((vr: any) => vr.success).length}/${response.verification_results.length} passed`);
          console.log(`[@useNode:executeNavigation] Overall result: ${verificationSuccess ? '✅ PASS' : '❌ FAIL'}`);
          
          if (verificationSuccess) {
            setNodeVerificationSuccess(selectedNode.id);
          } else {
            setNodeVerificationFailure(selectedNode.id);
          }
        }

        // Set edges to green for successful navigation
        if (navigationTransitions && navigationTransitions.length > 0) {
          setNavigationEdgesSuccess(navigationTransitions);
        }
      } catch (error: any) {
        console.error(`[@hook:useNode:executeNavigation] Navigation failed:`, error);
        const errorMessage = error.message || 'Navigation failed';
        setExecutionMessage(`Navigation failed: ${errorMessage}`);
        setNavigationError(errorMessage);
        
        // ✅ Extract debug report URL if available
        if (error.debugReportUrl) {
          console.log(`[@hook:useNode:executeNavigation] Debug report URL:`, error.debugReportUrl);
          setDebugReportUrl(error.debugReportUrl);
        } else {
          setDebugReportUrl(null);
        }
        
        setIsExecuting(false);

        // Set edges to red for failed navigation
        if (navigationTransitions && navigationTransitions.length > 0) {
          setNavigationEdgesFailure(navigationTransitions);
        }
      }
    },
    [
      props?.treeId,
      props?.selectedHost,
      props?.selectedDeviceId,
      currentNodeId,
      updateCurrentPosition,
      navigationTransitions,
      resetNavigationEdgeColors,
      setNavigationEdgesSuccess,
      setNavigationEdgesFailure,
      resetNodeVerificationColors,
      setNodeVerificationSuccess,
      setNodeVerificationFailure,
      navigationConfig.actualTreeId,
      isExecuting,
      userInterface,
      currentDeviceId,
      parentChain,
    ],
  );

  // Set up the navigation callback ref
  useEffect(() => {
    navigationCallbackRef.current = (nodeId: string) => {
      const targetNode = nodes.find((n: UINavigationNode) => n.id === nodeId);
      if (targetNode) {
        executeNavigation(targetNode);
      }
    };
  }, [nodes, executeNavigation]);

  /**
   * Clear navigation state when node changes
   */
  const clearNavigationState = useCallback(() => {
    setNavigationError(null);
    setDebugReportUrl(null);
    setExecutionMessage(null);
    // Clear navigation route indicators
    updateNodesWithMinimapIndicators([]);
  }, [updateNodesWithMinimapIndicators]);

  /**
   * Clear only navigation messages without affecting minimap indicators
   * Used when opening goto panel to clear previous messages but keep minimap unchanged
   */
  const clearNavigationMessages = useCallback(() => {
    setNavigationError(null);
    setExecutionMessage(null);
    // ❌ DON'T update minimap indicators when just clearing messages for preview
  }, []);

  /**
   * Check if node is an entry node
   */
  const isEntryNode = useCallback((node: UINavigationNode): boolean => {
    return node.type === 'entry';
  }, []);

  /**
   * Check if node is protected from deletion
   */
  const isProtectedNode = useCallback((node: UINavigationNode): boolean => {
    return (
      node.data.is_root ||
      node.type === 'entry' ||
      node.id === 'entry-node' ||
      node.data.label?.toLowerCase() === 'home' ||
      node.id?.toLowerCase().includes('entry') ||
      node.id?.toLowerCase().includes('home')
    );
  }, []);

  /**
   * Check button visibility states
   */
  const buttonVisibility = useMemo(() => {
    return {
      showSaveScreenshotButton: props?.isControlActive && props?.selectedHost,
      showGoToButton: props?.isControlActive && props?.selectedHost && props?.treeId,
      canRunGoto: props?.isControlActive && props?.selectedHost,
    };
  }, [props?.isControlActive, props?.selectedHost, props?.treeId]);

  /**
   * Get button visibility for a specific node
   */
  const getNodeButtonVisibility = useCallback((node: UINavigationNode) => {
    const isActionNode = node?.data?.type === 'action';
    
    return {
      showSaveScreenshotButton: buttonVisibility.showSaveScreenshotButton && !isActionNode,
      showGoToButton: buttonVisibility.showGoToButton && !isActionNode,
      canRunGoto: buttonVisibility.canRunGoto && !isActionNode,
    };
  }, [buttonVisibility]);

  const getButtonVisibility = useCallback(() => buttonVisibility, [buttonVisibility]);

  // Auto-clear screenshot status when node selection might change
  useEffect(() => {
    setScreenshotSaveStatus('idle');
  }, [props?.selectedHost, props?.selectedDeviceId]);

  return {
    // Core node operations
    getNodeFormWithVerifications,
    getParentNames,
    isProtectedNode,
    getButtonVisibility,
    getNodeButtonVisibility,

    // Screenshot operations
    takeAndSaveScreenshot,
    handleScreenshotConfirm,
    screenshotSaveStatus,

    // Model references
    modelReferences,
    referencesLoading,
    deviceModel,

    // NodeGotoPanel operations
    navigationTransitions,
    isLoadingPreview,
    isExecuting, // 🛡️ EXECUTION GUARD: Check this before allowing navigation operations
    navigationError,
    debugReportUrl,
    executionMessage,
    loadNavigationPreview,
    executeNavigation,
    clearNavigationState,
    getFullPath,

    // Current position information
    currentNodeId,
    updateCurrentPosition,
    updateNodesWithMinimapIndicators,

    // Additional helper functions
    isEntryNode,

    // New functions
    clearNavigationMessages,
  };
};
