import { useMemo, useCallback, useContext } from 'react';
import { MarkerType, addEdge, Connection } from 'reactflow';

import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import NavigationContext from '../../contexts/navigation/NavigationContext';
import { useHostManager } from '../useHostManager';
import { UINavigationEdge } from '../../types/pages/Navigation_Types';

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
            ...node.data // Additional data
          }
        }));

        const frontendEdges = treeData.edges.map((edge: any) => ({
          id: edge.edge_id,
          source: edge.source_node_id,
          target: edge.target_node_id,
          type: 'navigation',
          label: edge.label, // Move label to top-level (ReactFlow standard)
          sourceHandle: edge.data?.sourceHandle,
          targetHandle: edge.data?.targetHandle,
          data: {
            // Remove label from data - now in top-level field
            action_sets: edge.action_sets,
            default_action_set_id: edge.default_action_set_id,
            final_wait_time: edge.final_wait_time,
            ...edge.data
          }
        }));

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

      // Helper function to create edge data
      const createEdgeData = (sourceLabel: string, targetLabel: string, timestamp: number) => {
        const defaultActionSetId = `actionset-${timestamp}`;
        const actionSetLabel = `${sourceLabel}→${targetLabel}_1`;
        return {
          label: `${sourceLabel}→${targetLabel}`,
          action_sets: [
            {
              id: defaultActionSetId,
              label: actionSetLabel,
              actions: [],
              retry_actions: [],
        failure_actions: [],
              priority: 1,
            }
          ],
          default_action_set_id: defaultActionSetId,
          final_wait_time: 2000,
        };
      };

      // Determine if either node is an entry node, protected, or an action node
      const isSourceProtected = connection.source === 'entry-node' || 
                               sourceNode.data.label?.toLowerCase().includes('entry') ||
                               sourceNode.data.label?.toLowerCase().includes('home') ||
                               sourceNode.data.type === 'action';
      const isTargetProtected = connection.target === 'entry-node' || 
                               targetNode.data.label?.toLowerCase().includes('entry') ||
                               targetNode.data.label?.toLowerCase().includes('home') ||
                               targetNode.data.type === 'action';

      const timestamp = Date.now();

      // Create primary edge (original direction)
      const newEdge: UINavigationEdge = {
        id: `edge-${connection.source}-${connection.target}-${timestamp}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle || undefined,
        targetHandle: connection.targetHandle || undefined,
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
        data: createEdgeData(sourceNode.data.label, targetNode.data.label, timestamp),
      };

      console.log('[@useNavigationEditor:onConnect] Creating primary edge:', newEdge);

      let edgesToAdd = [newEdge];

      // Create bidirectional edge (reverse direction) unless one of the nodes is protected or an action
      // Protected nodes and action nodes should only have incoming edges, not outgoing bidirectional edges
      if (!isSourceProtected && !isTargetProtected) {
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

        const reverseSourceHandle = connection.targetHandle ? getCorrespondingSourceHandle(connection.targetHandle) : undefined;
        const reverseTargetHandle = connection.sourceHandle ? getCorrespondingTargetHandle(connection.sourceHandle) : undefined;

        console.log('[@useNavigationEditor:onConnect] Mapped handles for reverse edge:', {
          originalTargetHandle: connection.targetHandle,
          mappedToSourceHandle: reverseSourceHandle,
          originalSourceHandle: connection.sourceHandle,
          mappedToTargetHandle: reverseTargetHandle
        });

        const reverseEdge: UINavigationEdge = {
          id: `edge-${connection.target}-${connection.source}-${timestamp + 1}`,
          source: connection.target,
          target: connection.source,
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
          data: createEdgeData(targetNode.data.label, sourceNode.data.label, timestamp + 1),
        };

        console.log('[@useNavigationEditor:onConnect] Creating reverse edge:', reverseEdge);
        edgesToAdd.push(reverseEdge);
      } else {
        console.log('[@useNavigationEditor:onConnect] Skipping bidirectional edge due to protected/action node:', {
          sourceProtected: isSourceProtected,
          targetProtected: isTargetProtected,
          sourceType: sourceNode.data.type,
          targetType: targetNode.data.type
        });
      }

      // Handle parent inheritance based on handle direction: 
      // Vertical handles = parent-child relationship (inherit parent + source node)
      // Horizontal handles = sibling relationship (inherit same parent)
      let updatedNodes = navigation.nodes;
      const sourceParent = sourceNode.data.parent;
      const targetParent = targetNode.data.parent;
      
      // Determine if this is a vertical connection (top/bottom handles)
      const isVerticalConnection = connection.sourceHandle?.includes('top') || 
                                   connection.sourceHandle?.includes('bottom') ||
                                   connection.targetHandle?.includes('top') || 
                                   connection.targetHandle?.includes('bottom');

      if (!sourceParent && targetParent) {
        // Source node has no parent, inherit from target
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
        // Target node has no parent, inherit from source
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
      
      // Find bidirectional edge (opposite direction)
      const oppositeEdge = navigation.edges.find(
        (e) => e.source === edge.target && e.target === edge.source && e.id !== edge.id,
      );

      console.log('[@useNavigationEditor:onEdgeClick] Looking for opposite edge:', {
        source: edge.target,
        target: edge.source,
        excludeId: edge.id
      });
      console.log('[@useNavigationEditor:onEdgeClick] Found opposite edge:', oppositeEdge);

      if (oppositeEdge) {
        // Simple check: if any edge involves an action node, don't treat as bidirectional
        const sourceNode = navigation.nodes.find((n) => n.id === edge.source);
        const targetNode = navigation.nodes.find((n) => n.id === edge.target);
        const isActionInvolved = sourceNode?.data.type === 'action' || targetNode?.data.type === 'action';
        
        if (isActionInvolved) {
          // Action edges are unidirectional - just select the clicked edge
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
        
        // Auto-create reverse edge for non-action edges if needed
        const sourceNode = navigation.nodes.find((n) => n.id === edge.source);
        const targetNode = navigation.nodes.find((n) => n.id === edge.target);
        
        if (sourceNode && targetNode) {
          // Check if either node is protected or is an action node
          // Only protect actual entry nodes and action nodes, not all nodes containing "home"
          const isSourceProtected = edge.source === 'entry-node' || 
                                   sourceNode.data.label?.toLowerCase() === 'entry' ||
                                   sourceNode.data.type === 'action';
          const isTargetProtected = edge.target === 'entry-node' || 
                                   targetNode.data.label?.toLowerCase() === 'entry' ||
                                   targetNode.data.type === 'action';

          // Only create reverse edge if neither node is protected or an action
          if (!isSourceProtected && !isTargetProtected) {
            const timestamp = Date.now();
            const createEdgeData = (sourceLabel: string, targetLabel: string, timestamp: number) => {
              const defaultActionSetId = `actionset-${timestamp}`;
              const actionSetLabel = `${sourceLabel}→${targetLabel}_1`;
              return {
                label: `${sourceLabel}→${targetLabel}`,
                action_sets: [
                  {
                    id: defaultActionSetId,
                    label: actionSetLabel,
                    actions: [],
                    retry_actions: [],
        failure_actions: [],
                    priority: 1,
                  }
                ],
                default_action_set_id: defaultActionSetId,
                final_wait_time: 2000,
              };
            };

            console.log('[@useNavigationEditor:onEdgeClick] Original edge handles:', {
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle,
              targetHandle: edge.targetHandle
            });

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

            const reverseSourceHandle = edge.targetHandle ? getCorrespondingSourceHandle(edge.targetHandle) : undefined;
            const reverseTargetHandle = edge.sourceHandle ? getCorrespondingTargetHandle(edge.sourceHandle) : undefined;

            console.log('[@useNavigationEditor:onEdgeClick] Mapped handles for reverse edge:', {
              originalTargetHandle: edge.targetHandle,
              mappedToSourceHandle: reverseSourceHandle,
              originalSourceHandle: edge.sourceHandle,
              mappedToTargetHandle: reverseTargetHandle
            });

            const reverseEdge: UINavigationEdge = {
              id: `edge-${edge.target}-${edge.source}-${timestamp}`,
              source: edge.target,
              target: edge.source,
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
              data: createEdgeData(targetNode.data.label, sourceNode.data.label, timestamp),
            };

            console.log('[@useNavigationEditor:onEdgeClick] Auto-creating reverse edge:', reverseEdge);

            // Check if this edge ID already exists (shouldn't happen but let's be safe)
            const edgeExists = navigation.edges.find(e => e.id === reverseEdge.id);
            if (edgeExists) {
              console.warn('[@useNavigationEditor:onEdgeClick] Edge with this ID already exists!', reverseEdge.id);
              return;
            }

            // Add the reverse edge to navigation
            const updatedEdges = [...navigation.edges, reverseEdge];
            console.log('[@useNavigationEditor:onEdgeClick] Adding reverse edge to edges array. Total edges will be:', updatedEdges.length);
            navigation.setEdges(updatedEdges);
            navigation.setHasUnsavedChanges(true);

            // Set selected edge with the newly created bidirectional edge
            const edgeWithBidirectional = {
              ...edge,
              bidirectionalEdge: reverseEdge,
            };
            console.log('[@useNavigationEditor:onEdgeClick] Setting selected edge with auto-created bidirectional:', edgeWithBidirectional);
            navigation.setSelectedEdge(edgeWithBidirectional);
          } else {
            console.log('[@useNavigationEditor:onEdgeClick] Skipping auto-creation due to protected/action node:', {
              sourceProtected: isSourceProtected,
              targetProtected: isTargetProtected,
              sourceType: sourceNode.data.type,
              targetType: targetNode.data.type
            });
            navigation.setSelectedEdge(edge);
          }
        } else {
          console.log('[@useNavigationEditor:onEdgeClick] Could not find source or target node for auto-creation');
          navigation.setSelectedEdge(edge);
        }
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

    if (navigation.selectedNode) {
      const nodeId = navigation.selectedNode.id;
      const node = navigation.selectedNode;
      
      // Check if node has nested trees and warn user
      if (node.data?.has_subtree && (node.data?.subtree_count || 0) > 0) {
        const subtreeCount = node.data?.subtree_count || 0;
        const confirmMessage = `This node has ${subtreeCount} nested tree(s). Deleting it will also delete all nested navigation trees. Are you sure?`;
        if (!window.confirm(confirmMessage)) {
          return; // User cancelled
        }
        console.log(`[@useNavigationEditor:deleteSelected] User confirmed deletion of node with ${subtreeCount} nested trees`);
      }
      
      const filteredNodes = navigation.nodes.filter((n) => n.id !== nodeId);
      console.log('[@useNavigationEditor:deleteSelected] Deleting node:', nodeId, 
        'Nodes before:', navigation.nodes.length, 'Nodes after:', filteredNodes.length);
      navigation.setNodes(filteredNodes);
      navigation.setSelectedNode(null);
      navigation.markUnsavedChanges();
    }
    if (navigation.selectedEdge) {
      const mainEdge = navigation.selectedEdge;
      const bidirectionalEdge = mainEdge.bidirectionalEdge;
      
      // Helper function to check if an edge has actions
      const hasActions = (edge: any): boolean => {
        if (!edge?.data?.action_sets) return false;
        return edge.data.action_sets.some((actionSet: any) => 
          (actionSet.actions && actionSet.actions.length > 0) ||
          (actionSet.retry_actions && actionSet.retry_actions.length > 0) ||
          (actionSet.failure_actions && actionSet.failure_actions.length > 0)
        );
      };
      
      const mainHasActions = hasActions(mainEdge);
      const bidirectionalHasActions = bidirectionalEdge ? hasActions(bidirectionalEdge) : false;
      
      console.log('[@useNavigationEditor:deleteSelected] Edge deletion analysis:', {
        mainEdgeId: mainEdge.id,
        mainHasActions,
        bidirectionalEdgeId: bidirectionalEdge?.id,
        bidirectionalHasActions,
        currentEdgeCount: navigation.edges.length
      });
      
      let edgesToDelete: string[] = [];
      
      if (bidirectionalEdge) {
        // Bidirectional edge exists - apply smart deletion logic
        if (!mainHasActions && !bidirectionalHasActions) {
          // Both edges are empty - delete both (remove visual link completely)
          edgesToDelete = [mainEdge.id, bidirectionalEdge.id];
          console.log('[@useNavigationEditor:deleteSelected] Both edges empty - deleting both to remove visual link');
        } else if (!mainHasActions && bidirectionalHasActions) {
          // Main edge is empty, bidirectional has actions - only delete main edge
          edgesToDelete = [mainEdge.id];
          console.log('[@useNavigationEditor:deleteSelected] Main edge empty, bidirectional has actions - deleting only main edge');
        } else if (mainHasActions && !bidirectionalHasActions) {
          // Main edge has actions, bidirectional is empty - only delete bidirectional edge
          edgesToDelete = [bidirectionalEdge.id];
          console.log('[@useNavigationEditor:deleteSelected] Main edge has actions, bidirectional empty - deleting only bidirectional edge');
        } else {
          // Both edges have actions - ask for confirmation
          const confirmMessage = 'Both directions of this edge have configured actions. Delete both directions?';
          if (window.confirm(confirmMessage)) {
            edgesToDelete = [mainEdge.id, bidirectionalEdge.id];
            console.log('[@useNavigationEditor:deleteSelected] User confirmed deletion of both edges with actions');
          } else {
            console.log('[@useNavigationEditor:deleteSelected] User cancelled deletion of edges with actions');
            return; // User cancelled
          }
        }
      } else {
        // Single edge - delete it regardless of actions (existing behavior)
        edgesToDelete = [mainEdge.id];
        console.log('[@useNavigationEditor:deleteSelected] Single edge - deleting normally');
      }
      
      if (edgesToDelete.length > 0) {
        const filteredEdges = navigation.edges.filter((e) => !edgesToDelete.includes(e.id));
        console.log('[@useNavigationEditor:deleteSelected] Deleting edges:', edgesToDelete,
          'Edges before:', navigation.edges.length, 'Edges after:', filteredEdges.length);
        navigation.setEdges(filteredEdges);
        navigation.setSelectedEdge(null);
        navigation.markUnsavedChanges();
      }
    }
  }, [navigation]);

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
      
      // Centralized save methods from NavigationContext
      saveNodeWithStateUpdate: navigation.saveNodeWithStateUpdate,
      saveEdgeWithStateUpdate: navigation.saveEdgeWithStateUpdate,
      saveTreeWithStateUpdate: navigation.saveTreeWithStateUpdate,



      // Interface operations
      listAvailableTrees: async () => {
        try {
          const response = await fetch('/server/userinterface/getAllUserInterfaces');
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
    ],
  );
};
