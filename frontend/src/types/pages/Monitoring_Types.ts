/**
 * Monitoring Types
 *
 * Shared interfaces for monitoring functionality across the application.
 * These types correspond to the backend analysis data from analyze_audio_video.py
 */

// Core monitoring analysis from analyze_audio_video.py
export interface MonitoringAnalysis {
  timestamp: string;
  filename: string;
  thumbnail: string;
  blackscreen: boolean;
  blackscreen_percentage: number;
  freeze: boolean;
  freeze_diffs: number[];
  last_3_filenames: string[];
  last_3_thumbnails: string[]; // Local paths (deprecated, use r2_images)
  audio: boolean;
  volume_percentage: number;
  mean_volume_db: number;
  macroblocks: boolean; // Macroblock/image quality detection
  quality_score: number; // Image quality score (0-100)
  has_incidents: boolean; // Pre-calculated incident status
  
  // R2 storage URLs (for freeze incidents - uploaded to R2 on detection)
  r2_images?: {
    original_urls: string[];
    thumbnail_urls: string[];
    original_r2_paths: string[];
    thumbnail_r2_paths: string[];
    timestamp: string;
  };

  // Event duration tracking (from capture_monitor.py)
  blackscreen_event_start?: string;
  blackscreen_event_duration_ms?: number;
  freeze_event_start?: string;
  freeze_event_duration_ms?: number;
  audio_event_start?: string;
  audio_event_duration_ms?: number;
  macroblocks_event_start?: string;
  macroblocks_event_duration_ms?: number;

  // Action metadata (from action_executor.py)
  last_action_executed?: string;
  last_action_timestamp?: number;
  action_params?: Record<string, any>;
  
  // Zapping detection metadata (from zapping_detector_utils.py)
  zapping_detected?: boolean;
  zapping_channel_name?: string;
  zapping_channel_number?: string;
  zapping_program_name?: string;
  zapping_confidence?: number;
  zapping_blackscreen_duration_ms?: number;
  zapping_detection_type?: 'automatic' | 'manual';
  zapping_detected_at?: string; // ISO timestamp
}

// Subtitle analysis from backend detection (video.py) - EXACT field names
export interface SubtitleAnalysis {
  subtitles_detected: boolean; // result.subtitles_detected
  combined_extracted_text: string; // result.combined_extracted_text
  detected_language?: string; // result.detected_language
  confidence: number; // result.results[0].confidence
  detection_message?: string; // Clear message about detection status
}

// Frontend-computed subtitle trend analysis
export interface SubtitleTrendAnalysis {
  showRedIndicator: boolean;
  currentHasSubtitles: boolean;
  framesAnalyzed: number;
  noSubtitlesStreak: number;
}

// Language/subtitle menu analysis from backend AI detection - EXACT field names
export interface LanguageMenuAnalysis {
  menu_detected: boolean; // result.menu_detected
  audio_languages: string[]; // result.audio_languages (ordered list)
  subtitle_languages: string[]; // result.subtitle_languages (ordered list)
  selected_audio: number; // result.selected_audio (index or -1)
  selected_subtitle: number; // result.selected_subtitle (index or -1)
}

// Live monitoring events (zapping, etc.) - polled separately for real-time display
export interface LiveMonitoringEvent {
  event_id: string;
  event_type: 'zapping';
  timestamp: string; // ISO format
  frame_filename: string;
  detection_type: 'automatic' | 'manual';
  blackscreen_duration_ms: number;
  channel_name: string;
  channel_number: string;
  program_name: string;
  confidence: number;
  expires_at: number; // Unix timestamp
  
  // Only present for automatic zapping
  action_command?: string;
  action_timestamp?: number;
}

export interface LiveEventsResponse {
  success: boolean;
  events: LiveMonitoringEvent[];
  count: number;
}

// Alert/Incident types from backend alerts_db.py - EXACT field names
export interface Alert {
  id: string; // UUID from backend
  host_name: string; // Exact backend field name
  device_id: string; // Exact backend field name
  incident_type: string; // 'blackscreen' | 'freeze' | 'audio_loss'
  status: 'active' | 'resolved'; // Exact backend enum values
  consecutive_count: number; // Exact backend field name
  start_time: string; // ISO datetime string
  end_time?: string; // ISO datetime string (optional)
  metadata: AlertMetadata; // JSONB metadata from backend
  
  // AI Discard Analysis fields (from backend_discard service)
  checked?: boolean; // Whether AI has analyzed this alert
  check_type?: string; // Type of check performed ('ai' | 'manual')
  discard?: boolean; // Whether AI determined this is a false positive
  discard_type?: string; // Category of false positive ('brief_glitch' | 'channel_change' | etc.)
  discard_comment?: string; // AI explanation for the discard decision
  updated_at?: string; // When the discard analysis was performed
}

// Alert metadata structure (from alert_system.py)
export interface AlertMetadata {
  // Core analysis data (always present)
  blackscreen?: boolean;
  blackscreen_percentage?: number;
  freeze?: boolean;
  freeze_diffs?: number[];
  audio?: boolean;
  volume_percentage?: number;
  mean_volume_db?: number;
  last_3_filenames?: string[];
  last_3_thumbnails?: string[];

  // R2 storage URLs (for freeze incidents)
  r2_images?: {
    original_urls: string[];
    thumbnail_urls: string[];
    original_r2_paths: string[];
    thumbnail_r2_paths: string[];
    timestamp: string;
  };

  // Freeze detection details
  freeze_details?: {
    frames_compared: string[];
    frame_differences: number[];
    threshold: number;
    comparison_method: string;
  };

  // Allow additional metadata
  [key: string]: any;
}
