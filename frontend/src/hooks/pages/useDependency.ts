/**
 * Dependency Hook
 *
 * This hook handles all dependency analysis functionality for the dependency report.
 */

import { useState, useCallback } from 'react';

import { useExecutionResults } from './useExecutionResults';
import { useScriptResults } from './useScriptResults';
import { useUserInterface } from './useUserInterface';
import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';

// =====================================================
// DEPENDENCY INTERFACES
// =====================================================

export interface ScriptNodeDependency {
  script_result_id: string;
  script_name: string;
  userinterface_name: string | null;
  nodes: Array<{
    node_id: string;
    node_name: string;
    execution_count: number;
    success_rate: number;
  }>;
}

export interface ScriptEdgeDependency {
  script_result_id: string;
  script_name: string;
  userinterface_name: string | null;
  edges: Array<{
    edge_id: string;
    edge_name: string;
    execution_count: number;
    success_rate: number;
  }>;
}

export interface NodeScriptDependency {
  node_id: string;
  node_name: string;
  tree_name: string;
  scripts: Array<{
    script_result_id: string;
    script_name: string;
    execution_count: number;
    success_rate: number;
    html_report_r2_url: string | null;
  }>;
  total_executions: number;
  overall_success_rate: number;
}

export interface EdgeScriptDependency {
  edge_id: string;
  edge_name: string;
  tree_name: string;
  scripts: Array<{
    script_result_id: string;
    script_name: string;
    execution_count: number;
    success_rate: number;
    html_report_r2_url: string | null;
  }>;
  total_executions: number;
  overall_success_rate: number;
}

export interface DependencyData {
  scriptNodeDependencies: ScriptNodeDependency[];
  scriptEdgeDependencies: ScriptEdgeDependency[];
  nodeScriptDependencies: NodeScriptDependency[];
  edgeScriptDependencies: EdgeScriptDependency[];
}

// =====================================================
// HOOK IMPLEMENTATION
// =====================================================

export const useDependency = () => {
  const { getAllScriptResults } = useScriptResults();
  const { getAllExecutionResults } = useExecutionResults();
  const { getAllUserInterfaces } = useUserInterface();
  const navigationConfig = useNavigationConfig();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper function to get proper labels for nodes and edges
  const getElementLabel = useCallback(
    async (elementId: string, elementType: 'node' | 'edge', treeId: string, fallbackName?: string): Promise<string> => {
      // First, use the fallback name if available (this should be element_name from execution results)
      if (fallbackName) {
        return fallbackName;
      }

      try {
        // If no fallback, try to fetch from navigation data
        const treeData = await navigationConfig.loadTreeData(treeId);
        
        if (treeData.success) {
          if (elementType === 'node') {
            const node = treeData.nodes?.find((n: any) => n.node_id === elementId);
            if (node?.label) {
              return node.label;
            }
          } else if (elementType === 'edge') {
            const edge = treeData.edges?.find((e: any) => e.edge_id === elementId);
            if (edge?.label) {
              return edge.label;
            }
          }
        }
      } catch (error) {
        console.warn(`[@hook:useDependency] Failed to fetch ${elementType} label for ${elementId}:`, error);
      }

      // Last resort fallback
      return elementType === 'node' ? 'Unnamed Node' : 'Unnamed Edge';
    },
    [navigationConfig]
  );

  // Main function to load all dependency data
  const loadDependencyData = useCallback(async (): Promise<DependencyData> => {
    try {
      setLoading(true);
      setError(null);

      // Load script results, execution results, and user interfaces
      const [scriptResults, executionResults, userInterfaces] = await Promise.all([
        getAllScriptResults(),
        getAllExecutionResults(),
        getAllUserInterfaces(),
      ]);

      // Create mapping from tree_id to userinterface_name
      const treeMap: Record<string, string> = {};
      userInterfaces.forEach((ui) => {
        if (ui.root_tree?.id) {
          treeMap[ui.root_tree.id] = ui.name;
        }
      });

      // =====================================================
      // PROCESS SCRIPT → NODE DEPENDENCIES
      // =====================================================

      const scriptNodeDeps: ScriptNodeDependency[] = [];
      const scriptNodeMap = new Map<
        string,
        {
          script_name: string;
          userinterface_name: string | null;
          script_result_ids: string[];
          nodeExecutions: any[];
        }
      >();

      // Group by script name
      scriptResults.forEach((script) => {
        const nodeExecutions = executionResults.filter(
          (exec) =>
            exec.script_result_id === script.id &&
            exec.execution_type === 'verification' &&
            exec.node_id,
        );

        if (nodeExecutions.length > 0) {
          if (!scriptNodeMap.has(script.script_name)) {
            scriptNodeMap.set(script.script_name, {
              script_name: script.script_name,
              userinterface_name: script.userinterface_name,
              script_result_ids: [script.id],
              nodeExecutions: [],
            });
          }

          const existing = scriptNodeMap.get(script.script_name)!;
          existing.script_result_ids.push(script.id);
          existing.nodeExecutions.push(...nodeExecutions);
        }
      });

      // Process grouped scripts
      for (const [_scriptName, data] of scriptNodeMap.entries()) {
        const nodeMap = new Map<string, Array<{ success: boolean }>>();
        data.nodeExecutions.forEach((exec) => {
          if (!nodeMap.has(exec.node_id!)) {
            nodeMap.set(exec.node_id!, []);
          }
          nodeMap.get(exec.node_id!)!.push({ success: exec.success });
        });

        const nodes = await Promise.all(
          Array.from(nodeMap.entries()).map(async ([nodeId, executions]) => {
            const successCount = executions.filter((e) => e.success).length;
            const execution = data.nodeExecutions.find((e) => e.node_id === nodeId);
            const nodeName = await getElementLabel(
              nodeId,
              'node',
              execution?.tree_id || '',
              execution?.element_name
            );

            return {
              node_id: nodeId,
              node_name: nodeName,
              execution_count: executions.length,
              success_rate: (successCount / executions.length) * 100,
            };
          })
        );

        if (nodes.length > 0) {
          scriptNodeDeps.push({
            script_result_id: data.script_result_ids[0], // Use first ID for key
            script_name: data.script_name,
            userinterface_name: data.userinterface_name,
            nodes,
          });
        }
      }

      // =====================================================
      // PROCESS SCRIPT → EDGE DEPENDENCIES
      // =====================================================

      const scriptEdgeDeps: ScriptEdgeDependency[] = [];
      const scriptEdgeMap = new Map<
        string,
        {
          script_name: string;
          userinterface_name: string | null;
          script_result_ids: string[];
          edgeExecutions: any[];
        }
      >();

      // Group by script name
      scriptResults.forEach((script) => {
        const edgeExecutions = executionResults.filter(
          (exec) =>
            exec.script_result_id === script.id &&
            exec.execution_type === 'action' &&
            exec.edge_id,
        );

        if (edgeExecutions.length > 0) {
          if (!scriptEdgeMap.has(script.script_name)) {
            scriptEdgeMap.set(script.script_name, {
              script_name: script.script_name,
              userinterface_name: script.userinterface_name,
              script_result_ids: [script.id],
              edgeExecutions: [],
            });
          }

          const existing = scriptEdgeMap.get(script.script_name)!;
          existing.script_result_ids.push(script.id);
          existing.edgeExecutions.push(...edgeExecutions);
        }
      });

      // Process grouped scripts
      for (const [_scriptName, data] of scriptEdgeMap.entries()) {
        const edgeMap = new Map<string, Array<{ success: boolean }>>();
        data.edgeExecutions.forEach((exec) => {
          if (!edgeMap.has(exec.edge_id!)) {
            edgeMap.set(exec.edge_id!, []);
          }
          edgeMap.get(exec.edge_id!)!.push({ success: exec.success });
        });

        const edges = await Promise.all(
          Array.from(edgeMap.entries()).map(async ([edgeId, executions]) => {
            const successCount = executions.filter((e) => e.success).length;
            const execution = data.edgeExecutions.find((e) => e.edge_id === edgeId);
            const edgeName = await getElementLabel(
              edgeId,
              'edge',
              execution?.tree_id || '',
              execution?.element_name
            );

            return {
              edge_id: edgeId,
              edge_name: edgeName,
              execution_count: executions.length,
              success_rate: (successCount / executions.length) * 100,
            };
          })
        );

        if (edges.length > 0) {
          scriptEdgeDeps.push({
            script_result_id: data.script_result_ids[0], // Use first ID for key
            script_name: data.script_name,
            userinterface_name: data.userinterface_name,
            edges,
          });
        }
      }

      // =====================================================
      // PROCESS NODE → SCRIPTS DEPENDENCIES
      // =====================================================

      const nodeMap = new Map<
        string,
        {
          node_name: string;
          tree_name: string;
          script_executions: Array<{
            script_result_id: string;
            script_name: string;
            success: boolean;
            html_report_r2_url: string | null;
          }>;
        }
      >();

      // First, collect all unique nodes and their basic info
      const nodePromises = new Map<string, Promise<string>>();
      
      executionResults
        .filter((exec) => exec.execution_type === 'verification' && exec.node_id)
        .forEach((exec) => {
          if (!nodeMap.has(exec.node_id!)) {
            // Create a promise for the node name if we haven't already
            if (!nodePromises.has(exec.node_id!)) {
              nodePromises.set(
                exec.node_id!,
                getElementLabel(exec.node_id!, 'node', exec.tree_id, exec.element_name)
              );
            }
            
            nodeMap.set(exec.node_id!, {
              node_name: '', // Will be filled later
              tree_name: treeMap[exec.tree_id] || exec.tree_name,
              script_executions: [],
            });
          }

          const scriptInfo = scriptResults.find((s) => s.id === exec.script_result_id);
          if (scriptInfo) {
            nodeMap.get(exec.node_id!)!.script_executions.push({
              script_result_id: exec.script_result_id!,
              script_name: scriptInfo.script_name,
              success: exec.success,
              html_report_r2_url: scriptInfo.html_report_r2_url,
            });
          }
        });

      // Resolve all node name promises
      const nodeNameResults = await Promise.all(
        Array.from(nodePromises.entries()).map(async ([nodeId, namePromise]) => ({
          nodeId,
          name: await namePromise,
        }))
      );

      // Update nodeMap with resolved names
      nodeNameResults.forEach(({ nodeId, name }) => {
        const nodeData = nodeMap.get(nodeId);
        if (nodeData) {
          nodeData.node_name = name;
        }
      });

      const nodeScriptDeps: NodeScriptDependency[] = Array.from(nodeMap.entries()).map(
        ([nodeId, data]) => {
          // Group executions by script name
          const scriptGroups = new Map<
            string,
            Array<{
              success: boolean;
              html_report_r2_url: string | null;
              script_result_id: string;
            }>
          >();
          data.script_executions.forEach((exec) => {
            if (!scriptGroups.has(exec.script_name)) {
              scriptGroups.set(exec.script_name, []);
            }
            scriptGroups.get(exec.script_name)!.push({
              success: exec.success,
              html_report_r2_url: exec.html_report_r2_url,
              script_result_id: exec.script_result_id,
            });
          });

          const scripts = Array.from(scriptGroups.entries()).map(([scriptName, executions]) => {
            const successCount = executions.filter((e) => e.success).length;
            const htmlReport = executions[0]?.html_report_r2_url || null;

            return {
              script_result_id: executions[0].script_result_id, // Use first script_result_id for key
              script_name: scriptName,
              execution_count: executions.length,
              success_rate: (successCount / executions.length) * 100,
              html_report_r2_url: htmlReport,
            };
          });

          const totalExecutions = data.script_executions.length;
          const totalSuccesses = data.script_executions.filter((e) => e.success).length;

          return {
            node_id: nodeId,
            node_name: data.node_name,
            tree_name: data.tree_name,
            scripts,
            total_executions: totalExecutions,
            overall_success_rate:
              totalExecutions > 0 ? (totalSuccesses / totalExecutions) * 100 : 0,
          };
        },
      );

      // =====================================================
      // PROCESS EDGE → SCRIPTS DEPENDENCIES
      // =====================================================

      const edgeMap = new Map<
        string,
        {
          edge_name: string;
          tree_name: string;
          script_executions: Array<{
            script_result_id: string;
            script_name: string;
            success: boolean;
            html_report_r2_url: string | null;
          }>;
        }
      >();

      // First, collect all unique edges and their basic info
      const edgePromises = new Map<string, Promise<string>>();
      
      executionResults
        .filter((exec) => exec.execution_type === 'action' && exec.edge_id)
        .forEach((exec) => {
          if (!edgeMap.has(exec.edge_id!)) {
            // Create a promise for the edge name if we haven't already
            if (!edgePromises.has(exec.edge_id!)) {
              edgePromises.set(
                exec.edge_id!,
                getElementLabel(exec.edge_id!, 'edge', exec.tree_id, exec.element_name)
              );
            }
            
            edgeMap.set(exec.edge_id!, {
              edge_name: '', // Will be filled later
              tree_name: treeMap[exec.tree_id] || exec.tree_name,
              script_executions: [],
            });
          }

          const scriptInfo = scriptResults.find((s) => s.id === exec.script_result_id);
          if (scriptInfo) {
            edgeMap.get(exec.edge_id!)!.script_executions.push({
              script_result_id: exec.script_result_id!,
              script_name: scriptInfo.script_name,
              success: exec.success,
              html_report_r2_url: scriptInfo.html_report_r2_url,
            });
          }
        });

      // Resolve all edge name promises
      const edgeNameResults = await Promise.all(
        Array.from(edgePromises.entries()).map(async ([edgeId, namePromise]) => ({
          edgeId,
          name: await namePromise,
        }))
      );

      // Update edgeMap with resolved names
      edgeNameResults.forEach(({ edgeId, name }) => {
        const edgeData = edgeMap.get(edgeId);
        if (edgeData) {
          edgeData.edge_name = name;
        }
      });

      const edgeScriptDeps: EdgeScriptDependency[] = Array.from(edgeMap.entries()).map(
        ([edgeId, data]) => {
          // Group executions by script name
          const scriptGroups = new Map<
            string,
            Array<{
              success: boolean;
              html_report_r2_url: string | null;
              script_result_id: string;
            }>
          >();
          data.script_executions.forEach((exec) => {
            if (!scriptGroups.has(exec.script_name)) {
              scriptGroups.set(exec.script_name, []);
            }
            scriptGroups.get(exec.script_name)!.push({
              success: exec.success,
              html_report_r2_url: exec.html_report_r2_url,
              script_result_id: exec.script_result_id,
            });
          });

          const scripts = Array.from(scriptGroups.entries()).map(([scriptName, executions]) => {
            const successCount = executions.filter((e) => e.success).length;
            const htmlReport = executions[0]?.html_report_r2_url || null;

            return {
              script_result_id: executions[0].script_result_id, // Use first script_result_id for key
              script_name: scriptName,
              execution_count: executions.length,
              success_rate: (successCount / executions.length) * 100,
              html_report_r2_url: htmlReport,
            };
          });

          const totalExecutions = data.script_executions.length;
          const totalSuccesses = data.script_executions.filter((e) => e.success).length;

          return {
            edge_id: edgeId,
            edge_name: data.edge_name,
            tree_name: data.tree_name,
            scripts,
            total_executions: totalExecutions,
            overall_success_rate:
              totalExecutions > 0 ? (totalSuccesses / totalExecutions) * 100 : 0,
          };
        },
      );

      return {
        scriptNodeDependencies: scriptNodeDeps,
        scriptEdgeDependencies: scriptEdgeDeps,
        nodeScriptDependencies: nodeScriptDeps,
        edgeScriptDependencies: edgeScriptDeps,
      };
    } catch (err) {
      console.error('[@hook:useDependency] Error loading dependency data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dependency data';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [getAllScriptResults, getAllExecutionResults, getAllUserInterfaces, getElementLabel]);

  return {
    loadDependencyData,
    loading,
    error,
    setError,
  };
};
