export interface TestCase {
  test_id: string;
  name: string;
  test_type: 'functional' | 'performance' | 'endurance' | 'robustness';
  start_node: string;
  steps: {
    target_node: string;
    verify: {
      type: 'single' | 'compound';
      operator?: 'AND' | 'OR';
      conditions: { type: string; condition: string; timeout: number }[];
    };
  }[];
  // New fields for Phase 2 device integration
  device_name?: string;
  environment_profile_id?: string;
  verification_conditions?: VerificationCondition[];
  expected_results?: { [key: string]: any };
  execution_config?: { [key: string]: any };
  tags?: string[];
  priority?: number; // 1-5 scale
  estimated_duration?: number; // in seconds
  
  // AI-specific fields - clean modern implementation
  creator?: 'ai' | 'manual';
  original_prompt?: string;
  ai_analysis?: AIAnalysis;
  compatible_devices?: string[];
  compatible_userinterfaces?: string[];
  device_adaptations?: Record<string, any>;
}

export interface Campaign {
  campaign_id: string;
  name: string;
  description?: string;
  test_case_ids?: string[];
}

export interface Tree {
  tree_id: string;
  device: string;
  version: string;
  nodes: {
    [key: string]: {
      id: string;
      actions: {
        to: string;
        action: string;
        params: { [key: string]: any };
        verification: {
          type: 'single' | 'compound';
          operator?: 'AND' | 'OR';
          conditions: { type: string; condition: string; timeout: number }[];
        };
      }[];
    };
  };
}

// New interface for verification conditions
export interface VerificationCondition {
  id: string;
  type:
    | 'image_appears'
    | 'text_appears'
    | 'element_exists'
    | 'audio_playing'
    | 'video_playing'
    | 'color_present'
    | 'screen_state'
    | 'performance_metric';
  description: string;
  parameters: { [key: string]: any };
  timeout: number;
  critical: boolean; // If true, test fails if this condition fails
}

// AI-specific types - clean modern implementation
export interface AIAnalysis {
  analysis_id?: string;
  feasibility: 'possible' | 'impossible' | 'partial';
  reasoning: string;
  required_capabilities: string[];
  estimated_steps: number;
  generated_at: string;
  interface_specific?: boolean;
}

// Two-step analysis types
export interface AIAnalysisRequest {
  prompt: string;
}

export interface AIAnalysisResponse {
  analysis_id: string;
  understanding: string;
  compatibility_matrix: {
    compatible_userinterfaces: string[];
    incompatible: string[];
    reasons: Record<string, string>;
  };
  requires_multiple_testcases: boolean;
  estimated_complexity: 'low' | 'medium' | 'high';
  total_analyzed: number;
  compatible_count: number;
}

export interface AIGenerationRequest {
  analysis_id: string;
  confirmed_userinterfaces: string[];
}

export interface AIGenerationResponse {
  success: boolean;
  generated_testcases: TestCase[];
  total_generated: number;
  error?: string;
}

// Legacy types for compatibility
export interface AITestCaseRequest {
  prompt: string;
  device_model: string;
  interface_name: string;
}

export interface CompatibilityResult {
  interface_name: string;
  compatible: boolean;
  reasoning: string;
  missing_capabilities?: string[];
  required_nodes?: string[];
  available_nodes?: string[];
}

export interface AITestCaseResponse {
  success: boolean;
  test_case?: TestCase;
  compatibility_results?: CompatibilityResult[];
  error?: string;
}
