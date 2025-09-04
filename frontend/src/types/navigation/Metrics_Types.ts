/**
 * Navigation Metrics Types
 * Type definitions for database-driven confidence metrics
 */

// Raw metrics data from database
export interface RawNodeMetrics {
  node_id: string;
  tree_id: string;
  team_id: string;
  total_executions: number;
  successful_executions: number;
  success_rate: number; // decimal 0.0-1.0
  avg_execution_time_ms: number;
  created_at: string;
  updated_at: string;
}

export interface RawEdgeMetrics {
  edge_id: string;
  tree_id: string;
  team_id: string;
  total_executions: number;
  successful_executions: number;
  success_rate: number; // decimal 0.0-1.0
  avg_execution_time_ms: number;
  created_at: string;
  updated_at: string;
}

// Processed metrics for frontend use
export interface MetricData {
  id: string;
  volume: number; // total_executions
  success_rate: number; // 0.0-1.0
  avg_execution_time: number; // milliseconds
  confidence: number; // calculated confidence 0.0-1.0
  confidence_level: 'high' | 'medium' | 'low'; // based on thresholds
}

// Global tree metrics
export interface TreeMetrics {
  tree_id: string;
  total_nodes: number;
  total_edges: number;
  nodes_with_metrics: number;
  edges_with_metrics: number;
  global_confidence: number; // weighted average
  confidence_distribution: {
    high: number; // count of high confidence items
    medium: number; // count of medium confidence items
    low: number; // count of low confidence items
    untested: number; // count of items without metrics
  };
}

// API response types
export interface MetricsApiResponse {
  success: boolean;
  error?: string;
  tree_metrics: TreeMetrics;
  node_metrics: RawNodeMetrics[];
  edge_metrics: RawEdgeMetrics[];
}

// Low confidence items for modal display
export interface LowConfidenceItem {
  id: string;
  type: 'node' | 'edge';
  label: string;
  confidence: number;
  confidence_percentage: string; // formatted percentage
  volume: number;
  success_rate: number;
  avg_execution_time: number;
}

export interface LowConfidenceItems {
  nodes: LowConfidenceItem[];
  edges: LowConfidenceItem[];
  total_count: number;
}

// Confidence thresholds
export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.95, // >95% = high confidence (green)
  MEDIUM: 0.90, // 90-95% = medium confidence (orange)
  // <90% = low confidence (red)
} as const;

// Notification severity levels
export type NotificationSeverity = 'error' | 'warning' | 'info' | 'success';

export interface MetricsNotificationData {
  show: boolean;
  severity: NotificationSeverity;
  message: string;
  global_confidence: number;
  low_confidence_count: number;
  // Additional metrics for better display
  global_success_rate?: number;
  total_items?: number;
  confidence_distribution?: {
    high: number;
    medium: number;
    low: number;
    untested: number;
  };
}
