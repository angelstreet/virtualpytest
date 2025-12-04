import { useMemo, useCallback, useContext } from 'react';
import { MarkerType, addEdge, Connection } from 'reactflow';

import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import NavigationContext from '../../contexts/navigation/NavigationContext';
import { useHostManager } from '../useHostManager';
import { useConfirmDialog } from '../useConfirmDialog';
import { UINavigationEdge } from '../../types/pages/Navigation_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';

const normalizeAccents = (text: string) => {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

export const useNavigationEditor = () => {
  // Get the navigation config context (save/load functionality)
  const navigationConfig = useNavigationConfig();

  // Get the unified navigation context (state management)
  const navigation = useContext(NavigationContext);
  if (!navigation) {
    throw new Error('useNavigationEditor must be used within a NavigationProvider');
  }

  // Get host manager
  const hostManager = useHostManager();

  // Confirmation dialog for replacing window.confirm
  const { dialogState, confirm, handleConfirm, handleCancel } = useConfirmDialog();

  // Edge hook will be initialized when needed for edge operations

  // New normalized API functions
  const loadTreeData = useCallback(
    async (treeId: string) => {
      try {
        navigation.setIsLoading(true);
        navigation.setError(null);

        // Load complete tree data using new API
        const treeData = await navigationConfig.loadTreeData(treeId);
        
        // Convert normalized data to frontend format
        const frontendNodes = treeData.nodes.map((node: any) => ({
          id: node.node_id,
          type: node.node_type || 'screen', // Use node_type directly as ReactFlow type
          position: { x: node.position_x, y: node.position_y },
          data: {
            label: node.label,
            type: node.node_type || 'screen',
            description: node.description,
            verifications: node.verifications, // Directly embedded
            ...node.data // ✅ Spread data object which contains verification_pass_condition and other fields
          }
        }));

        console.log(`[@useNavigationEditor:loadTreeData] 📋 Loaded ${frontendNodes.length} nodes from database:`);
        frontendNodes.forEach((node: any) => {
          console.log(`[@useNavigationEditor:loadTreeData]   • ${node.id} (label: '${node.data.label}', type: '${node.type}')`);
        });

        const frontendEdges = treeData.edges.map((edge: any) => {
          // Check if edge is conditional (either primary or regular conditional)
          const isConditional = edge.data?.is_conditional || edge.data?.is_conditional_primary;
          
          if (isConditional) {
            console.log(`[@useNavigationEditor:loadTreeData] 🔵 Restoring conditional edge styling: ${edge.edge_id}`, {
              is_conditional: edge.data?.is_conditional,
              is_conditional_primary: edge.data?.is_conditional_primary,
              action_set_id: edge.action_sets?.[0]?.id
            });
          }
          
          return {
            id: edge.edge_id,
            source: edge.source_node_id,
            target: edge.target_node_id,
            type: 'navigation',
            label: edge.label, // Move label to top-level (ReactFlow standard)
            sourceHandle: edge.data?.sourceHandle,
            targetHandle: edge.data?.targetHandle,
            // Apply conditional styling if flags are set
            style: isConditional ? { stroke: '#2196f3', strokeWidth: 2 } : { stroke: '#555', strokeWidth: 2 },
            markerEnd: isConditional ? { type: 'arrowclosed' as const, color: '#2196f3' } : { type: 'arrowclosed' as const, color: '#555' },
            data: {
              // Remove label from data - now in top-level field
              action_sets: edge.action_sets,
              default_action_set_id: edge.default_action_set_id,
              final_wait_time: edge.final_wait_time,
              ...edge.data
            }
          };
        });

        navigation.setNodes(frontendNodes);
        navigation.setEdges(frontendEdges);
        navigation.setInitialState({ nodes: [...frontendNodes], edges: [...frontendEdges] });
        navigation.setHasUnsavedChanges(false);

        // Restore viewport if saved and ReactFlow is ready
        if (treeData.tree) {
          const { viewport_x, viewport_y, viewport_zoom } = treeData.tree;
          console.log(`[@useNavigationEditor:loadTreeData] Tree has viewport data:`, { viewport_x, viewport_y, viewport_zoom });
          
          if (viewport_x !== undefined && viewport_y !== undefined && viewport_zoom !== undefined) {
            // Use setTimeout to ensure React Flow is fully initialized
            setTimeout(() => {
              if (navigation.reactFlowInstance) {
                console.log(`[@useNavigationEditor:loadTreeData] Restoring viewport:`, { x: viewport_x, y: viewport_y, zoom: viewport_zoom });
                navigation.reactFlowInstance.setViewport({ x: viewport_x, y: viewport_y, zoom: viewport_zoom });
              } else {
                console.warn(`[@useNavigationEditor:loadTreeData] ReactFlow instance not available for viewport restoration`);
              }
            }, 100);
          } else {
            console.log(`[@useNavigationEditor:loadTreeData] No viewport data to restore`);
          }
        }

        console.log(`[@useNavigationEditor:loadTreeData] Loaded ${frontendNodes.length} nodes and ${frontendEdges.length} edges`);
        console.log('[@useNavigationEditor:loadTreeData] Set initialState with node IDs:', frontendNodes.map((n: any) => n.id));
      } catch (error) {
        navigation.setError(`Failed to load tree: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        navigation.setIsLoading(false);
      }
    },
    [navigationConfig, navigation],
  );

  const loadTreeByUserInterface = useCallback(
    async (userInterfaceId: string) => {
      try {
        navigation.setIsLoading(true);
        navigation.setError(null);

        // Load tree data by user interface using new API with metrics included (reduces 2 API calls to 1)
        const result = await navigationConfig.loadTreeByUserInterface(userInterfaceId, { includeMetrics: true });
        
        if (result.success && result.tree) {
          // Convert tree data to frontend format (same as loadTreeData)
          const treeData = result.tree;
          const frontendNodes = (treeData.metadata?.nodes || []).map((node: any) => ({
            id: node.node_id,
            type: node.node_type || 'screen',
            position: { x: node.position_x, y: node.position_y },
            data: {
              label: node.label,
              type: node.node_type || 'screen',
              description: node.description,
              verifications: node.verifications,
              ...node.data
            }
          }));

          const frontendEdges = (treeData.metadata?.edges || []).map((edge: any) => {
            // Check if edge is conditional (either primary or regular conditional)
            const isConditional = edge.data?.is_conditional || edge.data?.is_conditional_primary;
            
            return {
              id: edge.edge_id,
              source: edge.source_node_id,
              target: edge.target_node_id,
              type: 'navigation',
              label: edge.label,
              sourceHandle: edge.data?.sourceHandle,
              targetHandle: edge.data?.targetHandle,
              // Apply conditional styling if flags are set
              style: isConditional ? { stroke: '#2196f3', strokeWidth: 2 } : { stroke: '#555', strokeWidth: 2 },
              markerEnd: isConditional ? { type: 'arrowclosed' as const, color: '#2196f3' } : { type: 'arrowclosed' as const, color: '#555' },
              data: {
                action_sets: edge.action_sets,
                default_action_set_id: edge.default_action_set_id,
                final_wait_time: edge.final_wait_time,
                ...edge.data
              }
            };
          });

          navigation.setNodes(frontendNodes);
          navigation.setEdges(frontendEdges);
          navigation.setInitialState({ nodes: [...frontendNodes], edges: [...frontendEdges] });
          navigation.setHasUnsavedChanges(false);
          
          if (navigation.parentChain.length === 0) {
            navigation.addToParentChain({ 
              treeId: result.tree.id, 
              treeName: result.tree.name || userInterfaceId,
              nodes: frontendNodes, 
              edges: frontendEdges 
            });
          }

          if (result.metrics) {
            console.log(`[@useNavigationEditor:loadTreeByUserInterface] ✅ Received metrics in combined call - NO separate fetch needed!`, {
              nodeCount: Object.keys(result.metrics.nodes || {}).length,
              edgeCount: Object.keys(result.metrics.edges || {}).length,
              globalConfidence: result.metrics.global_confidence
            });
          }

          return result; // Return full result including metrics
        } else {
          throw new Error(result.error || 'Failed to load tree for user interface');
        }
      } catch (error) {
        navigation.setError(`Failed to load tree by user interface: ${error instanceof Error ? error.message : 'Unknown error'}`);
        throw error;
      } finally {
        navigation.setIsLoading(false);
      }
    },
    [navigationConfig, navigation],
  );









  // Simple event handlers
  const onConnect = useCallback(
    async (connection: Connection) => {
      console.log('Connection attempt:', connection);

      // Validate connection parameters
      if (!connection.source || !connection.target) {
        console.error(
          '[@useNavigationEditor:onConnect] Invalid connection: missing source or target',
        );
        return;
      }

      // Find source and target nodes
      const sourceNode = navigation.nodes.find((n) => n.id === connection.source);
      const targetNode = navigation.nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) {
        console.error('[@useNavigationEditor:onConnect] Source or target node not found');
        return;
      }

      // Prevent self-connections
      if (connection.source === connection.target) {
        console.warn('[@useNavigationEditor:onConnect] Cannot connect node to itself');
        return;
      }

      // Check if edge already exists in either direction to prevent duplicates
      const existingEdge = navigation.edges.find(
        (e) => 
          (e.source === connection.source && e.target === connection.target) ||
          (e.source === connection.target && e.target === connection.source)
      );

      if (existingEdge) {
        console.warn('[@useNavigationEditor:onConnect] Edge already exists between these nodes');
        return;
      }

      // 🔄 CONDITIONAL EDGE DETECTION: MANUAL ONLY (requires holding modifier key)
      // Conditional edges = same actions executed to multiple targets
      // User must hold Shift/Ctrl/Cmd while connecting to create conditional edge
      
      // Check if modifier key was held during connection (passed via connection object)
      const isConditionalEdge = (connection as any).isConditional || false;
      
      let conditionalActionSetId: string | null = null;
      let siblingEdges: any[] = [];
      let siblingActionsToShare: any = null;
      
      if (isConditionalEdge) {
        // MANUAL CONDITIONAL: Find sibling edges from same source to reuse action_set_id
        // CRITICAL: Only look at FORWARD edges (same source + sourceHandle) - ignore reverse
        siblingEdges = navigation.edges.filter(
          (e) => 
            e.source === connection.source && 
            e.sourceHandle === connection.sourceHandle &&
            e.target !== connection.target
        );
        
        if (siblingEdges.length > 0) {
          // Found sibling edge(s) - reuse their FORWARD action_set_id AND copy their FORWARD actions
          const firstSibling = siblingEdges[0];
          const siblingActionSets = firstSibling.data?.action_sets || [];
          
          // CRITICAL: Only use the FIRST action set (forward direction)
          // The second action set (reverse direction) is independent and NOT part of the conditional group
          if (siblingActionSets.length > 0) {
            const forwardActionSet = siblingActionSets[0]; // Always the forward direction
            conditionalActionSetId = forwardActionSet.id;
            
            // Copy FORWARD actions only (reverse direction is independent)
            siblingActionsToShare = {
              actions: forwardActionSet.actions || [],
              retry_actions: forwardActionSet.retry_actions || [],
              failure_actions: forwardActionSet.failure_actions || [],
            };
            console.log(`[@useNavigationEditor:onConnect] 🔗 CONDITIONAL edge - reusing FORWARD action_set_id: ${conditionalActionSetId}`);
            console.log(`[@useNavigationEditor:onConnect] 🔗 Copying ${siblingActionsToShare.actions.length} FORWARD actions from sibling`);
            console.log(`[@useNavigationEditor:onConnect] 🔗 ${siblingEdges.length + 1} edges will share this FORWARD action (reverse is independent)`);
          }
        }
      } else {
        console.log(`[@useNavigationEditor:onConnect] ✅ Regular edge - creating unique action sets`);
      }

      // Helper function to create bidirectional edge data
      const createEdgeData = (sourceLabel: string, targetLabel: string, conditionalSetId?: string | null, sharedActions?: any) => {
        // Clean labels for ID format
        const cleanSourceLabel = normalizeAccents(sourceLabel).toLowerCase().replace(/[^a-z0-9]/g, '_');
        const cleanTargetLabel = normalizeAccents(targetLabel).toLowerCase().replace(/[^a-z0-9]/g, '_');
        
        // CONDITIONAL EDGES: Only FORWARD action uses shared action_set_id
        // Reverse action ALWAYS gets unique ID (not part of conditional group)
        const forwardActionSetId = conditionalSetId || `${cleanSourceLabel}_to_${cleanTargetLabel}`;
        const reverseActionSetId = `${cleanTargetLabel}_to_${cleanSourceLabel}`; // Always unique
        
        return {
          label: `${sourceLabel}→${targetLabel}`,
          action_sets: [
            // FORWARD direction - may share action_set_id with sibling edges
            {
              id: forwardActionSetId,  // ✅ Shared ID for conditional edges
              label: `${sourceLabel} → ${targetLabel}`,
              // CRITICAL: Copy actions from sibling if this is a conditional edge
              actions: sharedActions?.actions || [],
              retry_actions: sharedActions?.retry_actions || [],
              failure_actions: sharedActions?.failure_actions || [],
            },
            // REVERSE direction - always unique (NOT part of conditional group)
            {
              id: reverseActionSetId,  // ✅ Always unique - reverse is independent
              label: `${targetLabel} → ${sourceLabel}`,
              actions: [],
              retry_actions: [],
              failure_actions: [],
            }
          ],
          default_action_set_id: forwardActionSetId,  // ✅ Use conditional ID as default
          final_wait_time: 2000,
          is_conditional: !!conditionalSetId,  // ✅ Mark as conditional edge (shares forward action only)
        };
      };

      // Simplified: no special handling needed since edges are now bidirectional by default

      const timestamp = Date.now();

      // Create single bidirectional edge (with conditional action_set_id if applicable)
      const newEdge: UINavigationEdge = {
        id: `edge-${connection.source}-${connection.target}-${timestamp}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle || undefined,
        targetHandle: connection.targetHandle || undefined,
        type: 'navigation',
        animated: false,
        style: {
          stroke: conditionalActionSetId ? '#2196f3' : '#555',  // 🎨 BLUE for conditional, gray for normal
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: conditionalActionSetId ? '#2196f3' : '#555',  // 🎨 Match marker color
        },
        data: createEdgeData(
          sourceNode?.data?.label || 'unknown', 
          targetNode?.data?.label || 'unknown',
          conditionalActionSetId,
          siblingActionsToShare
        ),
      };

      console.log('[@useNavigationEditor:onConnect] Creating edge:', newEdge);
      if (conditionalActionSetId) {
        console.log('[@useNavigationEditor:onConnect] 🔗 Edge is conditional - will verify all siblings on failure');
      }

      let edgesToAdd = [newEdge];
      
      // 🎨 Mark sibling edges as PRIMARY conditional edges
      // Primary edge: is_conditional_primary = true → BLUE + fully editable + no warning
      // Conditional edge: is_conditional = true → BLUE + shows warning popup
      let siblingEdgesToUpdate: UINavigationEdge[] = [];
      if (siblingEdges.length > 0) {
        siblingEdgesToUpdate = siblingEdges.map((edge) => ({
          ...edge,
          style: { ...edge.style, stroke: '#2196f3' },  // 🎨 BLUE (visual indicator)
          markerEnd: { ...edge.markerEnd, color: '#2196f3' },
          data: {
            ...edge.data,
            is_conditional_primary: true,  // ✅ Mark as PRIMARY conditional edge
          },
        }));
        console.log('[@useNavigationEditor:onConnect] 🎨 Will mark', siblingEdgesToUpdate.length, 'sibling edge(s) as PRIMARY conditional (BLUE + editable)');
      }
      console.log('[@useNavigationEditor:onConnect] Primary edge: BLUE + editable, Conditional edge: BLUE + warning popup');

      // No need for separate reverse edges - bidirectional logic is built into action sets
      if (false) { // Disabled complex reverse edge logic
        // Map target handles to their corresponding source handles
        const getCorrespondingSourceHandle = (targetHandle: string): string => {
          const handleMap: Record<string, string> = {
            'top-right-menu-target': 'top-left-menu-source',
            'bottom-left-menu-target': 'bottom-right-menu-source',
            'left-target': 'left-source',
            'right-target': 'right-source',
          };
          return handleMap[targetHandle] || targetHandle;
        };

        // Map source handles to their corresponding target handles  
        const getCorrespondingTargetHandle = (sourceHandle: string): string => {
          const handleMap: Record<string, string> = {
            'top-left-menu-source': 'top-right-menu-target',
            'bottom-right-menu-source': 'bottom-left-menu-target',
            'left-source': 'left-target',
            'right-source': 'right-target',
          };
          return handleMap[sourceHandle] || sourceHandle;
        };

        const reverseSourceHandle = connection.targetHandle ? getCorrespondingSourceHandle(connection.targetHandle as string) : undefined;
        const reverseTargetHandle = connection.sourceHandle ? getCorrespondingTargetHandle(connection.sourceHandle as string) : undefined;

        console.log('[@useNavigationEditor:onConnect] Mapped handles for reverse edge:', {
          originalTargetHandle: connection.targetHandle,
          mappedToSourceHandle: reverseSourceHandle,
          originalSourceHandle: connection.sourceHandle,
          mappedToTargetHandle: reverseTargetHandle
        });

        const reverseEdge: UINavigationEdge = {
          id: `edge-${connection.target}-${connection.source}-${timestamp + 1}`,
          source: connection.target ?? '',  // Add null check
          target: connection.source ?? '',  // Add null check
          // Use the mapped handles for the reverse direction
          sourceHandle: reverseSourceHandle,
          targetHandle: reverseTargetHandle,
          type: 'navigation',
          animated: false,
          style: {
            stroke: '#555',
            strokeWidth: 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#555',
          },
          data: createEdgeData(targetNode?.data?.label || 'unknown', sourceNode?.data?.label || 'unknown'),
        };

        console.log('[@useNavigationEditor:onConnect] Creating reverse edge:', reverseEdge);
        edgesToAdd.push(reverseEdge);
      } else {
        console.log('[@useNavigationEditor:onConnect] Simplified edge creation - no complex logic needed');
      }

      // Handle parent inheritance based on handle direction and ROOT NODE PRIORITY
      // 
      // ROOT NODE RULE: Root nodes are ALWAYS parents, never children
      // This includes:
      // 1. Main tree root nodes (is_root=true) - the home/entry node
      // 2. Nested tree root nodes (isParentReference=true) - parent node displayed in nested tree
      // 
      // This ensures that when linking to/from any root node, the root node is always 
      // treated as the parent, maintaining the navigation hierarchy correctly in both
      // main trees and nested subtrees.
      //
      // Standard logic (when no root nodes involved):
      // - Vertical handles = parent-child relationship (inherit parent + source node)
      // - Horizontal handles = sibling relationship (inherit same parent)
      let updatedNodes = navigation.nodes;
      const sourceParent = sourceNode.data.parent;
      const targetParent = targetNode.data.parent;
      
      // Check if either node is a root/home node
      // This includes:
      // 1. Main tree root nodes (is_root === true)
      // 2. Nested tree root nodes (isParentReference === true - parent node displayed in nested tree)
      const isSourceRoot = sourceNode.data.is_root === true || sourceNode.data.isParentReference === true;
      const isTargetRoot = targetNode.data.is_root === true || targetNode.data.isParentReference === true;
      
      // Determine if this is a vertical connection (top/bottom handles)
      const isVerticalConnection = connection.sourceHandle?.includes('top') || 
                                   connection.sourceHandle?.includes('bottom') ||
                                   connection.targetHandle?.includes('top') || 
                                   connection.targetHandle?.includes('bottom');

      // ROOT NODE PRIORITY: If either node is root, it becomes the parent
      if (isSourceRoot && !isTargetRoot) {
        // Source is root - it becomes parent of target
        const newParent = isVerticalConnection 
          ? [sourceNode.id] // Root becomes direct parent
          : (sourceParent || []); // For horizontal, target keeps same level as root
          
        const rootType = sourceNode.data.is_root ? 'main tree root' : 'nested tree root';
        console.log(`[@useNavigationEditor:onConnect] ROOT NODE: '${sourceNode.data.label}' (${rootType}) becomes parent of '${targetNode.data.label}':`, newParent);
        updatedNodes = navigation.nodes.map(node => 
          node.id === targetNode.id 
            ? { ...node, data: { ...node.data, parent: newParent } }
            : node
        );
        navigation.setNodes(updatedNodes);
      } else if (isTargetRoot && !isSourceRoot) {
        // Target is root - it becomes parent of source
        const newParent = isVerticalConnection 
          ? [targetNode.id] // Root becomes direct parent
          : (targetParent || []); // For horizontal, source keeps same level as root
          
        const rootType = targetNode.data.is_root ? 'main tree root' : 'nested tree root';
        console.log(`[@useNavigationEditor:onConnect] ROOT NODE: '${targetNode.data.label}' (${rootType}) becomes parent of '${sourceNode.data.label}':`, newParent);
        updatedNodes = navigation.nodes.map(node => 
          node.id === sourceNode.id 
            ? { ...node, data: { ...node.data, parent: newParent } }
            : node
        );
        navigation.setNodes(updatedNodes);
      } else if (isSourceRoot && isTargetRoot) {
        // Both are root nodes - no parent relationship changes
        console.log(`[@useNavigationEditor:onConnect] Both nodes are root nodes - no parent-child relationship established`);
      } else if (!sourceParent && targetParent) {
        // STANDARD LOGIC: Source node has no parent, inherit from target
        const newParent = isVerticalConnection 
          ? [...targetParent, targetNode.id] // Vertical: parent + target node (child relationship)
          : [...targetParent]; // Horizontal: same parent (sibling relationship)
          
        console.log(`[@useNavigationEditor:onConnect] Source node '${sourceNode.data.label}' inheriting ${isVerticalConnection ? 'child' : 'sibling'} relationship from '${targetNode.data.label}':`, newParent);
        updatedNodes = navigation.nodes.map(node => 
          node.id === sourceNode.id 
            ? { ...node, data: { ...node.data, parent: newParent } }
            : node
        );
        navigation.setNodes(updatedNodes);
      } else if (!targetParent && sourceParent) {
        // STANDARD LOGIC: Target node has no parent, inherit from source
        const newParent = isVerticalConnection 
          ? [...sourceParent, sourceNode.id] // Vertical: parent + source node (child relationship)
          : [...sourceParent]; // Horizontal: same parent (sibling relationship)
          
        console.log(`[@useNavigationEditor:onConnect] Target node '${targetNode.data.label}' inheriting ${isVerticalConnection ? 'child' : 'sibling'} relationship from '${sourceNode.data.label}':`, newParent);
        updatedNodes = navigation.nodes.map(node => 
          node.id === targetNode.id 
            ? { ...node, data: { ...node.data, parent: newParent } }
            : node
        );
        navigation.setNodes(updatedNodes);
      } else if (!sourceParent && !targetParent) {
        // Both nodes have no parent
        if (isVerticalConnection) {
          // For vertical connections, create parent-child relationship even without existing parents
          console.log(`[@useNavigationEditor:onConnect] Creating parent-child relationship: '${targetNode.data.label}' becomes parent of '${sourceNode.data.label}'`);
          updatedNodes = navigation.nodes.map(node => 
            node.id === sourceNode.id 
              ? { ...node, data: { ...node.data, parent: [targetNode.id] } }
              : node
          );
          navigation.setNodes(updatedNodes);
        } else {
          console.log(`[@useNavigationEditor:onConnect] Both nodes have no parent - no inheritance needed for horizontal connection`);
        }
      } else {
        console.log(`[@useNavigationEditor:onConnect] Both nodes already have parents - no inheritance needed`);
      }

      // Add all edges to current edges using ReactFlow's addEdge utility
      let updatedEdges = navigation.edges;
      
      // 🎨 First, apply sibling updates (mark as PRIMARY conditional)
      if (siblingEdgesToUpdate.length > 0) {
        updatedEdges = updatedEdges.map((edge) => {
          const updatedSibling = siblingEdgesToUpdate.find((s) => s.id === edge.id);
          return updatedSibling || edge;
        });
        console.log('[@useNavigationEditor:onConnect] 🎨 Marked', siblingEdgesToUpdate.length, 'edge(s) as PRIMARY conditional');
      }
      
      // Then add new edges
      for (const edge of edgesToAdd) {
        updatedEdges = addEdge(edge, updatedEdges) as UINavigationEdge[];
      }

      // Update edges in navigation context
      navigation.setEdges(updatedEdges);

      // Mark as having unsaved changes
      navigation.setHasUnsavedChanges(true);

      console.log(
        `[@useNavigationEditor:onConnect] ${edgesToAdd.length} edge(s) created successfully - manual save required`,
      );
    },
    [navigation],
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      navigation.setSelectedNode(node);
      navigation.setSelectedEdge(null); // Clear edge selection when node is selected
    },
    [navigation],
  );

  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: any) => {
      console.log('[@useNavigationEditor:onEdgeClick] Clicked edge:', edge);
      console.log('[@useNavigationEditor:onEdgeClick] All edges in navigation:', navigation.edges);
      console.log('[@useNavigationEditor:onEdgeClick] Clicked edge handles:', {
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle
      });
      
      // Find bidirectional edge (opposite direction) - DISABLED after migration
      // After migration, all edges contain both directions as action sets
      const oppositeEdge = null; // navigation.edges.find(
      //   (e) => e.source === edge.target && e.target === edge.source && e.id !== edge.id,
      // );

      console.log('[@useNavigationEditor:onEdgeClick] Looking for opposite edge:', {
        source: edge.target,
        target: edge.source,
        excludeId: edge.id
      });
      console.log('[@useNavigationEditor:onEdgeClick] Found opposite edge:', oppositeEdge);

      if (oppositeEdge) {
        // Simple check: if any edge involves an action or entry node, don't treat as bidirectional
        const sourceNode = navigation.nodes.find((n) => n.id === edge.source);
        const targetNode = navigation.nodes.find((n) => n.id === edge.target);
        const isUnidirectionalInvolved = (
          sourceNode?.type === 'action' || 
          targetNode?.type === 'action' ||
          sourceNode?.type === 'entry' || 
          targetNode?.type === 'entry'
        );
        
        if (isUnidirectionalInvolved) {
          // Action/entry edges are unidirectional - just select the clicked edge
          navigation.setSelectedEdge(edge);
        } else {
          // Regular edges can be bidirectional
          const edgeWithBidirectional = {
            ...edge,
            bidirectionalEdge: oppositeEdge,
          };
          navigation.setSelectedEdge(edgeWithBidirectional);
        }
      } else {
        // No opposite edge found - proceed with normal single edge selection
        navigation.setSelectedEdge(edge);
        

      }

      navigation.setSelectedNode(null); // Clear node selection when edge is selected
    },
    [navigation],
  );

  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      // Simple double-click opens edit dialog (nested navigation handled separately)
      navigation.openNodeDialog(node);
    },
    [navigation],
  );

  const onPaneClick = useCallback(() => {
    navigation.resetSelection();
  }, [navigation]);

  // Node and edge action handlers
  const handleNodeFormSubmit = useCallback(
    async (nodeForm: any) => {
      await navigation.saveNodeWithStateUpdate(nodeForm);
    },
    [navigation],
  );

  const handleEdgeFormSubmit = useCallback(
    async (edgeForm: any) => {
      await navigation.saveEdgeWithStateUpdate(edgeForm);
      // After save, update selectedEdge if this was the selected one
      const updatedEdge = navigation.edges.find(e => e.id === edgeForm.edgeId);
      if (updatedEdge && navigation.selectedEdge?.id === edgeForm.edgeId) {
        navigation.setSelectedEdge(updatedEdge);
      }
    },
    [navigation],
  );

  const addNewNode = useCallback(
    (type: string = 'screen', position: { x: number; y: number } = { x: 250, y: 250 }) => {
      const validType = type as 'screen' | 'menu' | 'entry' | 'action';
      const newNode = {
        id: `node-${Date.now()}`,
        type: validType, // Use the node type directly as ReactFlow type
        position,
        data: {
          type: validType,
          label: `new_${type}`,
          description: '',
          verifications: [],
        },
      };
      navigation.setNodes([...navigation.nodes, newNode as any]);
      navigation.markUnsavedChanges();
    },
    [navigation],
  );

  const cancelNodeChanges = useCallback(() => {
    navigation.setIsNodeDialogOpen(false);
    navigation.setNodeForm({
      label: '',
      type: 'screen',
      description: '',
      verifications: [],
    });
  }, [navigation]);

  const closeSelectionPanel = useCallback(() => {
    navigation.resetSelection();
  }, [navigation]);

  const deleteSelected = useCallback(async () => {
    console.log('[@useNavigationEditor:deleteSelected] Starting deletion process', {
      selectedNode: navigation.selectedNode?.id,
      selectedEdge: navigation.selectedEdge?.id,
      currentNodeCount: navigation.nodes.length,
      currentEdgeCount: navigation.edges.length
    });

    // Handle node deletion
    if (navigation.selectedNode) {
      const nodeId = navigation.selectedNode.id;
      const node = navigation.selectedNode;
      
      // ✅ PROTECTION: Prevent deletion of essential nodes (silently)
      if (nodeId === 'entry-node' || nodeId === 'home') {
        console.log(`[@useNavigationEditor:deleteSelected] Cannot delete protected node: ${nodeId}`);
        return;
      }
      
      // Check if node has nested trees and warn user
      if (node.data?.has_subtree && (node.data?.subtree_count || 0) > 0) {
        const subtreeCount = node.data?.subtree_count || 0;
        const confirmMessage = `This node has ${subtreeCount} nested tree(s). Deleting it will also delete all nested navigation trees. Are you sure?`;
        
        // Use custom confirm dialog instead of window.confirm
        return new Promise<void>((resolve) => {
          confirm({
            title: 'Delete Node with Nested Trees',
            message: confirmMessage,
            confirmColor: 'error',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            onConfirm: () => {
              console.log(`[@useNavigationEditor:deleteSelected] User confirmed deletion of node with ${subtreeCount} nested trees`);
              const filteredNodes = navigation.nodes.filter((n) => n.id !== nodeId);
              // Also delete edges connected to this node
              const filteredEdges = navigation.edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
              console.log('[@useNavigationEditor:deleteSelected] Deleting node:', nodeId, 
                'Nodes before:', navigation.nodes.length, 'Nodes after:', filteredNodes.length,
                'Edges before:', navigation.edges.length, 'Edges after:', filteredEdges.length);
              navigation.setNodes(filteredNodes);
              navigation.setEdges(filteredEdges);
              navigation.setSelectedNode(null);
              navigation.markUnsavedChanges();
              resolve();
            },
          });
        });
      }
      
      const filteredNodes = navigation.nodes.filter((n) => n.id !== nodeId);
      // Also delete edges connected to this node
      const filteredEdges = navigation.edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
      console.log('[@useNavigationEditor:deleteSelected] Deleting node:', nodeId, 
        'Nodes before:', navigation.nodes.length, 'Nodes after:', filteredNodes.length,
        'Edges before:', navigation.edges.length, 'Edges after:', filteredEdges.length);
      navigation.setNodes(filteredNodes);
      navigation.setEdges(filteredEdges);
      navigation.setSelectedNode(null);
      navigation.markUnsavedChanges();
    }

    // Handle edge deletion - DELEGATED TO useEdge
    if (navigation.selectedEdge) {
      const selectedEdge = navigation.selectedEdge;
      
      // ✅ PROTECTION: Prevent deletion of essential edge (silently)
      if (selectedEdge.id === 'edge-entry-node-to-home') {
        console.log(`[@useNavigationEditor:deleteSelected] Cannot delete protected edge: ${selectedEdge.id}`);
        return;
      }
      
      // Use custom confirm dialog instead of window.confirm
      return new Promise<void>((resolve) => {
        confirm({
          title: 'Delete Edge',
          message: 'Delete this entire edge and all its directions?',
          confirmColor: 'error',
          confirmText: 'Delete',
          cancelText: 'Cancel',
          onConfirm: () => {
            // Handle edge deletion directly without using the hook
            // Always delete the entire edge for simplicity in this context
            const deletionResult = { action: 'delete_entire_edge', edgeId: selectedEdge.id };
            
            console.log('[@useNavigationEditor:deleteSelected] Edge deletion result:', deletionResult);
            
            // Always delete the entire edge (simplified logic)
            if (deletionResult.action === 'delete_entire_edge') {
              const filteredEdges = navigation.edges.filter(e => e.id !== selectedEdge.id);
              navigation.setEdges(filteredEdges);
              navigation.setSelectedEdge(null);
              navigation.markUnsavedChanges();
              console.log('[@useNavigationEditor:deleteSelected] Edge deleted successfully');
            }
            resolve();
          },
        });
      });
    }
  }, [navigation, confirm]);

  const resetNode = useCallback(
    (nodeId: string) => {
      console.log('Reset node:', nodeId);
      navigation.setIsNodeDialogOpen(false);
    },
    [navigation],
  );

  const discardChanges = useCallback(() => {
    navigation.setIsDiscardDialogOpen(true);
  }, [navigation]);

  const performDiscardChanges = useCallback(() => {
    navigation.resetToInitialState();
    navigation.setIsDiscardDialogOpen(false);
  }, [navigation]);

  const fitView = useCallback(() => {
    navigation.fitViewToNodes();
  }, [navigation]);

  const navigateToParent = useCallback(() => {
    // Simple fallback
    console.log('Navigate to parent');
  }, []);

  const setUserInterfaceFromProps = useCallback(
    (userInterface: any) => {
      navigation.setUserInterface(userInterface);
    },
    [navigation],
  );

  // Combine all functionality into the same interface as the original useNavigationEditor
  return useMemo(
    () => ({
      // State (filtered views for ReactFlow display)
      nodes: navigation.nodes,
      edges: navigation.edges,

      // Raw data (single source of truth)
      allNodes: navigation.nodes, // In unified context, nodes are already the source of truth
      allEdges: navigation.edges,

      // Tree and interface state
      treeName: navigation.currentTreeName,
      treeId: navigation.currentTreeId,
      interfaceId: navigation.interfaceId,
      currentTreeId: navigation.currentTreeId,
      currentTreeName: navigation.currentTreeName,
      navigationPath: navigation.navigationPath,
      navigationNamePath: navigation.navigationNamePath,
      userInterface: navigation.userInterface,
      rootTree: navigation.rootTree,
      viewPath: navigation.viewPath,

      // Loading states
      isLoadingInterface: navigation.isLoadingInterface,
      isLoading: navigation.isLoading,

      // Selection state
      selectedNode: navigation.selectedNode,
      selectedEdge: navigation.selectedEdge,

      // Dialog states
      isNodeDialogOpen: navigation.isNodeDialogOpen,
      isEdgeDialogOpen: navigation.isEdgeDialogOpen,
      isDiscardDialogOpen: navigation.isDiscardDialogOpen,

      // Form states
      isNewNode: navigation.isNewNode,
      nodeForm: navigation.nodeForm,
      edgeForm: navigation.edgeForm,

      // Error and success states
      error: navigation.error,
      success: navigation.success,
      hasUnsavedChanges: navigation.hasUnsavedChanges,

      // Focus and filtering
      focusNodeId: navigation.focusNodeId,
      maxDisplayDepth: navigation.maxDisplayDepth,
      availableFocusNodes: navigation.availableFocusNodes,

      // React Flow refs and state
      reactFlowWrapper: navigation.reactFlowWrapper,
      reactFlowInstance: navigation.reactFlowInstance,
      pendingConnection: null, // Not used in unified context

      // Setters (maintain compatibility)
      setNodes: navigation.setNodes,
      setEdges: navigation.setEdges,
      setHasUnsavedChanges: navigation.setHasUnsavedChanges,
      setTreeName: navigation.setCurrentTreeName,
      setIsLoadingInterface: navigation.setIsLoadingInterface,
      setSelectedNode: navigation.setSelectedNode,
      setSelectedEdge: navigation.setSelectedEdge,
      setIsNodeDialogOpen: navigation.setIsNodeDialogOpen,
      setIsEdgeDialogOpen: navigation.setIsEdgeDialogOpen,
      setIsNewNode: navigation.setIsNewNode,
      setNodeForm: navigation.setNodeForm,
      setEdgeForm: navigation.setEdgeForm,
      setIsLoading: navigation.setIsLoading,
      setError: navigation.setError,
      setSuccess: navigation.setSuccess,
      setPendingConnection: () => {}, // Not used
      setReactFlowInstance: navigation.setReactFlowInstance,
      setIsDiscardDialogOpen: navigation.setIsDiscardDialogOpen,

      // Event handlers
      onNodesChange: navigation.onNodesChange,
      onEdgesChange: navigation.onEdgesChange,
      onConnect,
      onNodeClick,
      onEdgeClick,
      onNodeDoubleClick,
      onPaneClick,

      // Focus management
      setFocusNode: navigation.setFocusNodeId,
      setDisplayDepth: navigation.setMaxDisplayDepth,
      resetFocus: () => {
        navigation.setFocusNodeId(null);
        navigation.setMaxDisplayDepth(5);
      },
      isNodeDescendantOf: () => false, // Not implemented in unified context

      // New normalized API operations
      loadTreeData,
      loadTreeByUserInterface,
      
      // Centralized save methods from NavigationContext
      saveNodeWithStateUpdate: navigation.saveNodeWithStateUpdate,
      saveEdgeWithStateUpdate: navigation.saveEdgeWithStateUpdate,
      saveTreeWithStateUpdate: navigation.saveTreeWithStateUpdate,



      // Interface operations
      listAvailableTrees: async () => {
        try {
          const response = await fetch(buildServerUrl('/server/userinterface/getAllUserInterfaces'));
          if (!response.ok) {
            throw new Error(`Failed to fetch user interfaces: ${response.status}`);
          }
          return await response.json();
        } catch (error) {
          console.error('Error fetching user interfaces:', error);
          return [];
        }
      },

      // Lock management - from NavigationContext
      isLocked: navigation.isLocked,
      lockNavigationTree: navigation.lockNavigationTree,
      unlockNavigationTree: navigation.unlockNavigationTree,

      // Node/Edge management actions
      handleNodeFormSubmit,
      handleEdgeFormSubmit,
      handleDeleteNode: deleteSelected,
      handleDeleteEdge: deleteSelected,
      addNewNode,
      cancelNodeChanges,
      closeSelectionPanel,
      deleteSelected,
      resetNode,

      // Additional actions
      discardChanges,
      performDiscardChanges,
      fitView,

      // Navigation actions
      navigateToTreeLevel: () => {}, // Not implemented
      goBackToParent: navigateToParent,
      navigateToParentView: navigateToParent,
      navigateToParent,

      // Configuration
      defaultEdgeOptions: {
        type: 'navigation',
        animated: false,
        style: { strokeWidth: 2, stroke: '#b1b1b7' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: '#b1b1b7',
        },
      },

      // Connection rules
      getConnectionRulesSummary: () => 'No specific connection rules defined',

      // User interface management
      setUserInterfaceFromProps,

      // Device control state - from HostManager
      selectedHost: hostManager.selectedHost,
      isControlActive: hostManager.isControlActive,
      isRemotePanelOpen: hostManager.isRemotePanelOpen,
      showRemotePanel: hostManager.showRemotePanel,
      showAVPanel: hostManager.showAVPanel,
      isVerificationActive: false, // Not implemented

      // Device control handlers - from HostManager
      handleDeviceSelect: hostManager.handleDeviceSelect,
      handleControlStateChange: hostManager.handleControlStateChange,
      handleToggleRemotePanel: hostManager.handleToggleRemotePanel,
      handleConnectionChange: () => {}, // Not implemented
      handleDisconnectComplete: hostManager.handleDisconnectComplete,

      // Host data - from HostManager (filtered by userInterface models)
      availableHosts: hostManager.getHostsByModel(navigation.userInterface?.models || []),
      getHostByName: hostManager.getHostByName,

      // Confirmation dialog state and handlers
      confirmDialogState: dialogState,
      confirmDialogHandleConfirm: handleConfirm,
      confirmDialogHandleCancel: handleCancel,
    }),
    [
      navigation,
      navigationConfig,
      hostManager,
      loadTreeData,
      onConnect,
      onNodeClick,
      onEdgeClick,
      onNodeDoubleClick,
      onPaneClick,
      handleNodeFormSubmit,
      handleEdgeFormSubmit,
      addNewNode,
      cancelNodeChanges,
      closeSelectionPanel,
      deleteSelected,
      resetNode,
      discardChanges,
      performDiscardChanges,
      fitView,
      navigateToParent,
      setUserInterfaceFromProps,
      dialogState,
      handleConfirm,
      handleCancel,
    ],
  );
};
