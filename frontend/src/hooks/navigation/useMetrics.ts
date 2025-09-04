/**
 * Navigation Metrics Hook
 * Fetches and manages database-driven confidence metrics for nodes and edges
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

import {
  MetricData,
  TreeMetrics,
  MetricsApiResponse,
  LowConfidenceItems,
  MetricsNotificationData,
} from '../../types/navigation/Metrics_Types';
import { UINavigationNode, UINavigationEdge } from '../../types/pages/Navigation_Types';
import {
  processNodeMetrics,
  processEdgeMetrics,
  calculateGlobalConfidence,
  getLowConfidenceItems,
  generateNotificationData,
} from '../../utils/metricsCalculations';

export interface UseMetricsProps {
  treeId?: string | null;
  nodes?: UINavigationNode[];
  edges?: UINavigationEdge[];
  enabled?: boolean; // Allow disabling metrics fetching
}

export const useMetrics = (props?: UseMetricsProps) => {
  const { treeId, nodes = [], edges = [], enabled = true } = props || {};

  // State
  const [nodeMetrics, setNodeMetrics] = useState<Map<string, MetricData>>(new Map());
  const [edgeMetrics, setEdgeMetrics] = useState<Map<string, MetricData>>(new Map());
  const [treeMetrics, setTreeMetrics] = useState<TreeMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedTreeId, setLastFetchedTreeId] = useState<string | null>(null);

  /**
   * Fetch metrics from backend API
   */
  const fetchMetrics = useCallback(async (targetTreeId: string) => {
    if (!targetTreeId || !enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      console.log(`[@useMetrics] Fetching metrics for tree: ${targetTreeId}`);
      
      const response = await fetch(`/server/metrics/tree/${targetTreeId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch metrics');
      }

      console.log(`[@useMetrics] Received metrics:`, {
        nodeCount: Object.keys(data.nodes || {}).length,
        edgeCount: Object.keys(data.edges || {}).length,
        globalConfidence: data.global_confidence || 0,
        distribution: data.confidence_distribution || {},
        hierarchyInfo: data.hierarchy_info || null
      });
      
      // Log hierarchy information if present
      if (data.hierarchy_info) {
        console.log(`[@useMetrics] Hierarchy: ${data.hierarchy_info.total_trees} trees, max depth: ${data.hierarchy_info.max_depth}, nested: ${data.hierarchy_info.has_nested_trees}`);
        if (data.hierarchy_info.trees) {
          data.hierarchy_info.trees.forEach((tree: any) => {
            console.log(`[@useMetrics] - Tree: ${tree.name} (depth: ${tree.depth}, root: ${tree.is_root})`);
          });
        }
      }

      // Convert backend format to frontend MetricData format (no processing needed)
      const processedNodeMetrics = new Map<string, MetricData>();
      if (data.nodes) {
        for (const [nodeId, nodeMetric] of Object.entries(data.nodes)) {
          const metric = nodeMetric as any; // Backend format
          processedNodeMetrics.set(nodeId, {
            id: nodeId,
            volume: metric.volume,
            success_rate: metric.success_rate,
            avg_execution_time: metric.avg_execution_time,
            confidence: metric.confidence, // Backend calculated
            confidence_level: metric.confidence >= 0.7 ? 'high' : metric.confidence >= 0.49 ? 'medium' : 'low'
          });
        }
      }

      // Convert backend format to frontend MetricData format (no processing needed)
      const processedEdgeMetrics = new Map<string, MetricData>();
      if (data.edges) {
        for (const [edgeId, edgeMetric] of Object.entries(data.edges)) {
          const metric = edgeMetric as any; // Backend format
          processedEdgeMetrics.set(edgeId, {
            id: edgeId,
            volume: metric.volume,
            success_rate: metric.success_rate,
            avg_execution_time: metric.avg_execution_time,
            confidence: metric.confidence, // Backend calculated
            confidence_level: metric.confidence >= 0.7 ? 'high' : metric.confidence >= 0.49 ? 'medium' : 'low'
          });
        }
      }

      // Update state
      setNodeMetrics(processedNodeMetrics);
      setEdgeMetrics(processedEdgeMetrics);
      
      // Set tree metrics from backend global confidence
      const treeMetrics = data.global_confidence !== undefined ? {
        tree_id: targetTreeId,
        global_confidence: data.global_confidence,
        confidence_distribution: data.confidence_distribution || {
          high: 0,
          medium: 0,
          low: 0,
          untested: 0
        },
        total_nodes: Object.keys(data.nodes || {}).length,
        total_edges: Object.keys(data.edges || {}).length,
        nodes_with_metrics: Object.values(data.nodes || {}).filter((n: any) => n.volume > 0).length,
        edges_with_metrics: Object.values(data.edges || {}).filter((e: any) => e.volume > 0).length
      } : null;
      
      setTreeMetrics(treeMetrics);
      setLastFetchedTreeId(targetTreeId);

      console.log(`[@useMetrics] Metrics processed successfully for tree: ${targetTreeId}`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error(`[@useMetrics] Failed to fetch metrics:`, errorMessage);
      setError(errorMessage);
      
      // Clear metrics on error
      setNodeMetrics(new Map());
      setEdgeMetrics(new Map());
      setTreeMetrics(null);
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  /**
   * Auto-fetch metrics when treeId changes
   */
  useEffect(() => {
    if (treeId && treeId !== lastFetchedTreeId && enabled) {
      fetchMetrics(treeId);
    }
  }, [treeId, lastFetchedTreeId, fetchMetrics, enabled]);

  /**
   * Calculate global confidence from current metrics
   */
  const globalConfidence = useMemo(() => {
    if (treeMetrics?.global_confidence !== undefined) {
      return treeMetrics.global_confidence;
    }
    
    // Fallback: calculate from current metrics
    return calculateGlobalConfidence(nodeMetrics, edgeMetrics);
  }, [nodeMetrics, edgeMetrics, treeMetrics]);

  /**
   * Get low confidence items for modal display
   */
  const lowConfidenceItems = useMemo((): LowConfidenceItems => {
    return getLowConfidenceItems(nodeMetrics, edgeMetrics, nodes, edges);
  }, [nodeMetrics, edgeMetrics, nodes, edges]);

  /**
   * Generate notification data
   */
  const notificationData = useMemo((): MetricsNotificationData => {
    return generateNotificationData(globalConfidence, lowConfidenceItems.total_count);
  }, [globalConfidence, lowConfidenceItems.total_count]);

  /**
   * Get metrics for a specific node
   */
  const getNodeMetrics = useCallback((nodeId: string): MetricData | null => {
    return nodeMetrics.get(nodeId) || null;
  }, [nodeMetrics]);

  /**
   * Get metrics for a specific edge
   */
  const getEdgeMetrics = useCallback((edgeId: string): MetricData | null => {
    return edgeMetrics.get(edgeId) || null;
  }, [edgeMetrics]);

  /**
   * Check if metrics are available for a node
   */
  const hasNodeMetrics = useCallback((nodeId: string): boolean => {
    return nodeMetrics.has(nodeId);
  }, [nodeMetrics]);

  /**
   * Check if metrics are available for an edge
   */
  const hasEdgeMetrics = useCallback((edgeId: string): boolean => {
    return edgeMetrics.has(edgeId);
  }, [edgeMetrics]);

  /**
   * Refresh metrics for current tree
   */
  const refreshMetrics = useCallback(() => {
    if (treeId) {
      fetchMetrics(treeId);
    }
  }, [treeId, fetchMetrics]);

  /**
   * Clear all metrics data
   */
  const clearMetrics = useCallback(() => {
    setNodeMetrics(new Map());
    setEdgeMetrics(new Map());
    setTreeMetrics(null);
    setError(null);
    setLastFetchedTreeId(null);
  }, []);

  /**
   * Get metrics summary for debugging
   */
  const getMetricsSummary = useCallback(() => {
    return {
      treeId: lastFetchedTreeId,
      nodeMetricsCount: nodeMetrics.size,
      edgeMetricsCount: edgeMetrics.size,
      globalConfidence,
      lowConfidenceCount: lowConfidenceItems.total_count,
      isLoading,
      error,
    };
  }, [
    lastFetchedTreeId,
    nodeMetrics.size,
    edgeMetrics.size,
    globalConfidence,
    lowConfidenceItems.total_count,
    isLoading,
    error,
  ]);

  return {
    // Core metrics data
    nodeMetrics,
    edgeMetrics,
    treeMetrics,
    globalConfidence,
    lowConfidenceItems,
    notificationData,

    // State
    isLoading,
    error,
    lastFetchedTreeId,

    // Getter functions
    getNodeMetrics,
    getEdgeMetrics,
    hasNodeMetrics,
    hasEdgeMetrics,

    // Actions
    fetchMetrics,
    refreshMetrics,
    clearMetrics,

    // Utilities
    getMetricsSummary,
  };
};
