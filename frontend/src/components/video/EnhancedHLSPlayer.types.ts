import { Host } from '../../types/common/Host_Types';
import { MonitoringAnalysis, SubtitleAnalysis, LanguageMenuAnalysis } from '../../types/pages/Monitoring_Types';

export interface ArchiveMetadata {
  total_segments: number;
  total_duration_seconds: number;
  window_hours: number;
  segments_per_window: number;
  manifests: Array<{
    name: string;
    window_index: number;
    chunk_index: number;
    start_segment: number;
    end_segment: number;
    start_time_seconds: number;
    end_time_seconds: number;
    duration_seconds: number;
  }>;
}

export interface TranscriptSegment {
  segment_num: number;
  relative_seconds: number;
  language: string;
  transcript: string;
  enhanced_transcript?: string;
  confidence: number;
  manifest_window: number;
  translations?: Record<string, string>;
}

// OLD format (6-second segments)
export interface TranscriptDataLegacy {
  capture_folder: string;
  sample_interval_seconds: number;
  total_duration_seconds: number;
  segments: TranscriptSegment[];
  last_update: string;
  total_samples: number;
}

// NEW format (10-minute single transcript per chunk)
export interface TranscriptData10Min {
  capture_folder: string;
  hour: number;
  chunk_index: number;
  chunk_duration_minutes: number;
  language: string;
  transcript: string;
  confidence: number;
  transcription_time_seconds: number;
  timestamp: string;
  mp3_file: string;
  translations?: Record<string, string>;
}

// Union type for backward compatibility
export type TranscriptData = TranscriptDataLegacy | TranscriptData10Min;

export interface ErrorTrendData {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
  macroblocksConsecutive: number;
  hasWarning: boolean;
  hasError: boolean;
}

export interface EnhancedHLSPlayerProps {
  deviceId: string;
  hostName: string;
  host?: Host;
  streamUrl?: string;
  width?: string | number;
  height?: string | number;
  muted?: boolean;
  className?: string;
  isLiveMode?: boolean;
  quality?: 'low' | 'sd' | 'hd';
  shouldPause?: boolean;
  onPlayerReady?: () => void;
  onVideoTimeUpdate?: (time: number) => void;
  onVideoPause?: () => void;
  
  monitoringMode?: boolean;
  monitoringAnalysis?: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
  errorTrendData?: ErrorTrendData | null;
  analysisTimestamp?: string | null;
  isAIAnalyzing?: boolean;
}
