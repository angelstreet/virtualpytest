/**
 * Metrics Calculations Utilities
 * Functions for calculating confidence levels and processing metrics data
 */

import {
  RawNodeMetrics,
  RawEdgeMetrics,
  MetricData,
  LowConfidenceItem,
  LowConfidenceItems,
  CONFIDENCE_THRESHOLDS,
  MetricsNotificationData,
} from '../types/navigation/Metrics_Types';
import { UINavigationNode, UINavigationEdge } from '../types/pages/Navigation_Types';

/**
 * Calculate confidence based on volume and success rate
 * Your requirements: volume + test success = confidence
 */
export const calculateConfidence = (
  totalExecutions: number,
  successRate: number,
): number => {
  // Volume weight: reaches 1.0 at 10 executions, caps at 1.0
  const volumeWeight = Math.min(totalExecutions / 10, 1.0);
  
  // Success rate weight: direct mapping 0.0-1.0
  const successWeight = successRate;
  
  // Combined confidence: 30% volume importance, 70% success importance
  const confidence = (volumeWeight * 0.3) + (successWeight * 0.7);
  
  return Math.min(confidence, 1.0); // Cap at 1.0
};

/**
 * Determine confidence level from confidence score
 */
export const getConfidenceLevel = (confidence: number): 'high' | 'medium' | 'low' => {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return 'high';
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return 'medium';
  return 'low';
};

/**
 * Convert raw node metrics to processed MetricData
 */
export const processNodeMetrics = (rawMetrics: RawNodeMetrics): MetricData => {
  const confidence = calculateConfidence(rawMetrics.total_executions, rawMetrics.success_rate);
  
  return {
    id: rawMetrics.node_id,
    volume: rawMetrics.total_executions,
    success_rate: rawMetrics.success_rate,
    avg_execution_time: rawMetrics.avg_execution_time_ms,
    confidence,
    confidence_level: getConfidenceLevel(confidence),
  };
};

/**
 * Convert raw edge metrics to processed MetricData
 */
export const processEdgeMetrics = (rawMetrics: RawEdgeMetrics): MetricData => {
  const confidence = calculateConfidence(rawMetrics.total_executions, rawMetrics.success_rate);
  
  return {
    id: rawMetrics.edge_id,
    volume: rawMetrics.total_executions,
    success_rate: rawMetrics.success_rate,
    avg_execution_time: rawMetrics.avg_execution_time_ms,
    confidence,
    confidence_level: getConfidenceLevel(confidence),
  };
};

/**
 * Calculate global confidence from all metrics
 */
export const calculateGlobalConfidence = (
  nodeMetrics: Map<string, MetricData>,
  edgeMetrics: Map<string, MetricData>,
): number => {
  const allMetrics = [...nodeMetrics.values(), ...edgeMetrics.values()];
  
  if (allMetrics.length === 0) return 0;
  
  // Weighted average based on execution volume
  let totalWeightedConfidence = 0;
  let totalWeight = 0;
  
  for (const metric of allMetrics) {
    const weight = Math.max(metric.volume, 1); // Minimum weight of 1
    totalWeightedConfidence += metric.confidence * weight;
    totalWeight += weight;
  }
  
  return totalWeight > 0 ? totalWeightedConfidence / totalWeight : 0;
};

/**
 * Get low confidence items for modal display
 */
export const getLowConfidenceItems = (
  nodeMetrics: Map<string, MetricData>,
  edgeMetrics: Map<string, MetricData>,
  nodes: UINavigationNode[],
  edges: UINavigationEdge[],
  threshold: number = CONFIDENCE_THRESHOLDS.MEDIUM,
): LowConfidenceItems => {
  const lowConfidenceNodes: LowConfidenceItem[] = [];
  const lowConfidenceEdges: LowConfidenceItem[] = [];
  
  // Process nodes
  for (const [nodeId, metrics] of nodeMetrics.entries()) {
    if (metrics.confidence < threshold) {
      const node = nodes.find(n => n.id === nodeId);
      if (node) {
        lowConfidenceNodes.push({
          id: nodeId,
          type: 'node',
          label: node.data.label,
          confidence: metrics.confidence,
          confidence_percentage: `${(metrics.confidence * 100).toFixed(1)}%`,
          volume: metrics.volume,
          success_rate: metrics.success_rate,
          avg_execution_time: metrics.avg_execution_time,
        });
      }
    }
  }
  
  // Process edges
  for (const [edgeId, metrics] of edgeMetrics.entries()) {
    if (metrics.confidence < threshold) {
      const edge = edges.find(e => e.id === edgeId);
      if (edge) {
        // Create edge label from source/target node labels
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        const edgeLabel = edge.label || 
          `${sourceNode?.data.label || 'Unknown'} → ${targetNode?.data.label || 'Unknown'}`;
        
        lowConfidenceEdges.push({
          id: edgeId,
          type: 'edge',
          label: edgeLabel,
          confidence: metrics.confidence,
          confidence_percentage: `${(metrics.confidence * 100).toFixed(1)}%`,
          volume: metrics.volume,
          success_rate: metrics.success_rate,
          avg_execution_time: metrics.avg_execution_time,
        });
      }
    }
  }
  
  // Sort by confidence (lowest first)
  lowConfidenceNodes.sort((a, b) => a.confidence - b.confidence);
  lowConfidenceEdges.sort((a, b) => a.confidence - b.confidence);
  
  return {
    nodes: lowConfidenceNodes,
    edges: lowConfidenceEdges,
    total_count: lowConfidenceNodes.length + lowConfidenceEdges.length,
  };
};

/**
 * Generate notification data based on global confidence and metrics
 */
export const generateNotificationData = (
  globalConfidence: number,
  lowConfidenceCount: number,
  nodeMetrics?: Map<string, MetricData>,
  edgeMetrics?: Map<string, MetricData>,
): MetricsNotificationData => {
  // Calculate global success rate from all metrics
  const allMetrics = [...(nodeMetrics?.values() || []), ...(edgeMetrics?.values() || [])];
  const metricsWithData = allMetrics.filter(m => m.volume > 0);
  
  let globalSuccessRate = 0;
  if (metricsWithData.length > 0) {
    const totalWeightedSuccess = metricsWithData.reduce((sum, m) => sum + (m.success_rate * m.volume), 0);
    const totalVolume = metricsWithData.reduce((sum, m) => sum + m.volume, 0);
    globalSuccessRate = totalVolume > 0 ? totalWeightedSuccess / totalVolume : 0;
  }
  
  // Calculate confidence distribution
  const confidenceDistribution = {
    high: allMetrics.filter(m => m.confidence >= 0.7).length,
    medium: allMetrics.filter(m => m.confidence >= 0.49 && m.confidence < 0.7).length,
    low: allMetrics.filter(m => m.confidence < 0.49 && m.volume > 0).length,
    untested: allMetrics.filter(m => m.volume === 0).length,
  };
  
  // Don't show notification if there are no metrics at all (0.0% with 0 items)
  if (globalConfidence === 0 && lowConfidenceCount === 0) {
    return {
      show: false,
      severity: 'info',
      message: '',
      global_confidence: globalConfidence,
      low_confidence_count: lowConfidenceCount,
      global_success_rate: globalSuccessRate,
      total_items: allMetrics.length,
      confidence_distribution: confidenceDistribution,
    };
  }
  
  // Don't show notification if confidence is high
  if (globalConfidence >= CONFIDENCE_THRESHOLDS.HIGH) {
    return {
      show: false,
      severity: 'success',
      message: '',
      global_confidence: globalConfidence,
      low_confidence_count: lowConfidenceCount,
      global_success_rate: globalSuccessRate,
      total_items: allMetrics.length,
      confidence_distribution: confidenceDistribution,
    };
  }
  
  const confidenceScore = Math.round(globalConfidence * 10); // Convert to 0-10 scale, whole number
  const successRatePercent = (globalSuccessRate * 100).toFixed(0);
  
  // Show error notification for low confidence (only if there are actual items)
  if (globalConfidence < CONFIDENCE_THRESHOLDS.MEDIUM && lowConfidenceCount > 0) {
    return {
      show: true,
      severity: 'error',
      message: `Confidence Score: ${confidenceScore}/10 • Success Rate: ${successRatePercent}% • ${lowConfidenceCount} items need attention`,
      global_confidence: globalConfidence,
      low_confidence_count: lowConfidenceCount,
      global_success_rate: globalSuccessRate,
      total_items: allMetrics.length,
      confidence_distribution: confidenceDistribution,
    };
  }
  
  // Show warning notification for medium confidence (only if there are actual items)
  if (lowConfidenceCount > 0) {
    return {
      show: true,
      severity: 'warning',
      message: `Confidence Score: ${confidenceScore}/10 • Success Rate: ${successRatePercent}% • ${lowConfidenceCount} items below 90%`,
      global_confidence: globalConfidence,
      low_confidence_count: lowConfidenceCount,
      global_success_rate: globalSuccessRate,
      total_items: allMetrics.length,
      confidence_distribution: confidenceDistribution,
    };
  }
  
  // No notification needed - good confidence or no problematic items
  return {
    show: false,
    severity: 'success',
    message: '',
    global_confidence: globalConfidence,
    low_confidence_count: lowConfidenceCount,
    global_success_rate: globalSuccessRate,
    total_items: allMetrics.length,
    confidence_distribution: confidenceDistribution,
  };
};

/**
 * Format execution time for display
 */
export const formatExecutionTime = (timeMs: number): string => {
  if (timeMs < 1000) return `${timeMs}ms`;
  if (timeMs < 60000) return `${(timeMs / 1000).toFixed(1)}s`;
  return `${(timeMs / 60000).toFixed(1)}m`;
};

/**
 * Format success rate for display
 */
export const formatSuccessRate = (rate: number): string => {
  return `${(rate * 100).toFixed(1)}%`;
};

/**
 * Get confidence color for UI elements
 */
export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return '#4caf50'; // Green
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return '#ff9800'; // Orange
  return '#f44336'; // Red
};
