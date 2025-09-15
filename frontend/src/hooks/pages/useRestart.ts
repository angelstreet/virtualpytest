import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../useToast';

// =====================================================
// TYPES & INTERFACES
// =====================================================

interface UseRestartParams {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

interface AudioAnalysis {
  success: boolean;
  combined_transcript: string;
  detected_language: string;
  speech_detected: boolean;
  confidence: number;
  execution_time_ms: number;
}

interface SubtitleAnalysis {
  success: boolean;
  subtitles_detected: boolean;
  extracted_text: string;
  detected_language?: string;
  execution_time_ms: number;
  frame_subtitles?: string[];
}

interface VideoDescriptionAnalysis {
  frame_descriptions: string[];
  video_summary: string;
  frames_analyzed: number;
  execution_time_ms: number;
}

interface AnalysisResults {
  audio: AudioAnalysis | null;
  subtitles: SubtitleAnalysis | null;
  videoDescription: VideoDescriptionAnalysis | null;
}

type AnalysisState = 'idle' | 'loading' | 'completed' | 'error';

interface AnalysisProgress {
  video: AnalysisState;
  audio: AnalysisState;
  subtitles: AnalysisState;
  summary: AnalysisState;
  report: AnalysisState;
}

interface BackendAnalysisData {
  audio_analysis?: {
    success: boolean;
    combined_transcript: string;
    detected_language: string;
    speech_detected: boolean;
    confidence: number;
    segments_analyzed: number;
  };
  subtitle_analysis?: {
    success: boolean;
    subtitles_detected: boolean;
    extracted_text: string;
    detected_language: string;
    confidence: number;
    frames_analyzed: number;
    frame_subtitles?: string[];
  };
  video_analysis?: {
    success: boolean;
    frame_descriptions: string[];
    video_summary: string;
    frames_analyzed: number;
  };
  screenshot_urls?: string[];
  video_id?: string;
  segment_count?: number;
  analysis_complete?: boolean;
}

interface BackendResponse {
  success: boolean;
  video_url?: string;
  processing_time_seconds?: number;
  analysis_data?: BackendAnalysisData;
  report_url?: string;
  error?: string;
}

interface TranslationResults {
  transcript: string;
  summary: string;
  frameDescriptions: string[];
  frameSubtitles: string[];
}

interface UseRestartReturn {
  // Core video state
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
  reportUrl: string | null;
  
  // Analysis state
  analysisResults: AnalysisResults;
  analysisProgress: AnalysisProgress;
  isAnalysisComplete: boolean;
  
  // Dubbing state
  dubbedVideos: Record<string, string>;
  dubbedAudioUrls: Record<string, { gtts: string; edge: string }>;
  isDubbing: boolean;
  
  // Translation state
  translationResults: Record<string, TranslationResults>;
  isTranslating: boolean;
  currentLanguage: string;
  
  // Audio timing state
  audioTimingOffset: number;
  isApplyingTiming: boolean;
  
  // Manual analysis triggers
  analyzeAudio: (videoUrl: string) => Promise<any>;
  analyzeSubtitles: (videoUrl: string) => Promise<any>;
  analyzeVideoDescription: (videoUrl: string) => Promise<any>;
  
  // Translation function
  translateToLanguage: (language: string) => Promise<void>;
  
  // Dubbing function
  generateDubbedVersion: (language: string, transcript: string, videoId: string) => Promise<void>;
  
  // Audio timing function
  applyAudioTiming: (offsetMs: number) => Promise<void>;
  
  // Utility functions
  regenerateVideo: () => Promise<void>;
}

// =====================================================
// CACHE MANAGEMENT
// =====================================================

interface CacheEntry {
  promise: Promise<BackendResponse>;
  timestamp: number;
}

class VideoGenerationCache {
  private cache = new Map<string, CacheEntry>();
  private readonly CACHE_TTL = 30000; // 30 seconds

  private generateKey(host: Host, device: Device): string {
    return `${host.host_name}-${device.device_id}`;
  }

  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > this.CACHE_TTL;
  }

  get(host: Host, device: Device): Promise<BackendResponse> | null {
    const key = this.generateKey(host, device);
    const entry = this.cache.get(key);
    
    if (!entry || this.isExpired(entry)) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.promise;
  }

  set(host: Host, device: Device, promise: Promise<BackendResponse>): void {
    const key = this.generateKey(host, device);
    this.cache.set(key, {
      promise,
      timestamp: Date.now()
    });
  }

  delete(host: Host, device: Device): void {
    const key = this.generateKey(host, device);
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }
}

// Global cache instance
const videoCache = new VideoGenerationCache();


// =====================================================
// MAIN HOOK IMPLEMENTATION
// =====================================================

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  // =====================================================
  // STATE MANAGEMENT
  // =====================================================
  
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime] = useState<number | null>(null);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  
  // Dubbing state
  const [dubbedVideos, setDubbedVideos] = useState<Record<string, string>>({});
  const [dubbedAudioUrls, setDubbedAudioUrls] = useState<Record<string, { gtts: string; edge: string }>>({});
  const [isDubbing, setIsDubbing] = useState(false);
  
  // Translation state
  const [translationResults, setTranslationResults] = useState<Record<string, TranslationResults>>({});
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentLanguage, setCurrentLanguage] = useState('en');
  
  // Audio timing state
  const [audioTimingOffset, setAudioTimingOffset] = useState(0);
  const [isApplyingTiming, setIsApplyingTiming] = useState(false);
  
  // Translation deduplication protection
  const isTranslationInProgress = useRef(false);
  const currentTranslationLanguage = useRef<string | null>(null);
  
  // Request deduplication to prevent React StrictMode duplicate calls
  const isRequestInProgress = useRef(false);
  const hasExecutedOnMount = useRef(false);
  
  // Report generation deduplication protection
  const isReportGenerationInProgress = useRef(false);
  const currentReportVideoId = useRef<string | null>(null);
  
  // Toast notifications and timing
  const toast = useToast();
  const analysisStartTime = useRef<number | null>(null);
  
  const [analysisResults, setAnalysisResults] = useState<AnalysisResults>({
    audio: null,
    subtitles: null,
    videoDescription: null,
  });
  
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    video: 'idle',
    audio: 'idle',
    subtitles: 'idle',
    summary: 'idle',
    report: 'idle',
  });

  // =====================================================
  // CORE FUNCTIONS
  // =====================================================

  const generateReportInBackground = useCallback(async (reportKey: string, videoData: any, audioData: any, combinedData: any) => {
    try {
      console.log(`[@hook:useRestart] 📊 Starting report generation for ${reportKey}`);
      setAnalysisProgress(prev => ({ ...prev, report: 'loading' }));
      toast.showInfo('📊 Generating report...', { duration: 3000 });
      
      const reportResponse = await fetch(buildServerUrl('/server/restart/generateRestartReport'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id || 'device1',
          video_url: videoData.video_url,
          analysis_data: {
            audio_analysis: audioData.audio_analysis,
            subtitle_analysis: combinedData.subtitle_analysis,
            video_analysis: combinedData.video_analysis,
          }
        })
      });
      
      const reportData = await reportResponse.json();
      
      if (reportData.success && reportData.report_url) {
        setReportUrl(reportData.report_url);
        setAnalysisProgress(prev => ({ ...prev, report: 'completed' }));
        console.log(`[@hook:useRestart] ✅ Report generation completed: ${reportData.report_url}`);
        toast.showSuccess('📊 Report ready!', { duration: 4000 });
      } else {
        setAnalysisProgress(prev => ({ ...prev, report: 'error' }));
        console.log(`[@hook:useRestart] ❌ Report generation failed: ${reportData.error || 'Unknown error'}`);
        toast.showError('❌ Report generation failed', { duration: 5000 });
      }
    } catch (reportError) {
      setAnalysisProgress(prev => ({ ...prev, report: 'error' }));
      console.error(`[@hook:useRestart] ❌ Report generation error:`, reportError);
      toast.showError('❌ Report generation failed', { duration: 5000 });
    } finally {
      // Clear report generation flags
      isReportGenerationInProgress.current = false;
      currentReportVideoId.current = null;
    }
  }, [host, device, toast]);

  const executeVideoGeneration = useCallback(async () => {
    // Prevent duplicate calls (React StrictMode protection)
    if (isRequestInProgress.current) {
      console.log(`[@hook:useRestart] Request already in progress, ignoring duplicate call`);
      return;
    }

    // Mark request as in progress (no abort controller needed with proper deduplication)
    isRequestInProgress.current = true;

    const videoGenerationStartTime = Date.now();
    console.log(`[@hook:useRestart] Starting 4-stage video generation for ${host.host_name}-${device.device_id}`);
    
    setIsGenerating(true);
    setError(null);
    setIsReady(false);
    setAnalysisProgress({ video: 'loading', audio: 'idle', subtitles: 'idle', summary: 'idle', report: 'idle' });

    try {
      // Stage 1: Generate video only (fast)
      const videoResponse = await fetch(buildServerUrl('/server/restart/generateRestartVideo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id || 'device1',
          duration_seconds: 10,
        })
      });

      if (!videoResponse.ok) throw new Error(`Video generation failed: ${videoResponse.status}`);
      const videoData = await videoResponse.json();
      
      if (!videoData.success) throw new Error(videoData.error || 'Video generation failed');

      // Video ready - show immediately (FAST LAUNCH)
      const videoGenerationDuration = ((Date.now() - videoGenerationStartTime) / 1000).toFixed(1);
      console.log(`[@hook:useRestart] ✅ Video ready! Launching player immediately: ${videoData.video_url}`);
      console.log(`[@hook:useRestart] 🎬 Video generated in ${videoGenerationDuration}s`);
      
      setVideoUrl(videoData.video_url);
      setIsReady(true);
      setAnalysisProgress(prev => ({ ...prev, video: 'completed' }));
      
      // Show success toast with generation time
      toast.showSuccess(`🎬 Video generated in ${videoGenerationDuration}s`, { duration: 4000 });
      
      // Keep "generating" state visible for 1.5 seconds so user sees the process
      setTimeout(() => {
        console.log(`[@hook:useRestart] 🎬 Switching from "generating" to "ready" state`);
        setIsGenerating(false);
      }, 1500);

      if (!includeAudioAnalysis) {
        console.log(`[@hook:useRestart] ✅ Analysis disabled - video player ready for immediate use`);
        return;
      }

      // Show toast notification and start timing for AI analysis
      analysisStartTime.current = Date.now();
      
      // Small delay to ensure video player renders smoothly before starting heavy analysis
      console.log(`[@hook:useRestart] 🎬 Allowing video player to render before starting analysis...`);
      await new Promise(resolve => setTimeout(resolve, 100)); // 100ms delay
      
      toast.showInfo('🤖 AI Analysis starting...', { duration: 3000 });

      // Stage 2-4: Run analysis sequentially (no race conditions)
      console.log(`[@hook:useRestart] Starting sequential analysis for video_id: ${videoData.video_id}`);
      const segmentFiles = videoData.analysis_data?.segment_files || [];
      console.log(`[@hook:useRestart] Segment files available:`, segmentFiles.length);
      if (segmentFiles.length > 0) {
        console.log(`[@hook:useRestart] First segment file:`, segmentFiles[0]);
        console.log(`[@hook:useRestart] Last segment file:`, segmentFiles[segmentFiles.length - 1]);
      } else {
        console.warn(`[@hook:useRestart] ⚠️  No segment files received - audio analysis will fall back to globbing`);
      }
      
      try {
        // Step 2: Audio Analysis
        console.log(`[@hook:useRestart] Step 2: Starting audio analysis`);
        console.log(`[@hook:useRestart] Step 2: Passing ${segmentFiles.length} segment files to audio analysis`);
        setAnalysisProgress(prev => ({ ...prev, audio: 'loading' }));
        
        const audioResponse = await fetch(buildServerUrl('/server/restart/analyzeRestartAudio'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host,
            device_id: device.device_id || 'device1',
            video_id: videoData.video_id,
            segment_files: segmentFiles.length > 0 ? segmentFiles : null, // Pass segment files from video generation
          }),
        });
        
        const audioData = await audioResponse.json();
        
        // Handle duplicate request (409) - treat as success since analysis is already running
        if (audioResponse.status === 409 && audioData.code === 'DUPLICATE_REQUEST') {
          console.log(`[@hook:useRestart] Step 2: Audio analysis already in progress, skipping`);
          setAnalysisProgress(prev => ({ ...prev, audio: 'completed' }));
        } else if (audioData.success && audioData.audio_analysis) {
          setAnalysisResults(prev => ({ ...prev, audio: {
            success: audioData.audio_analysis.success,
            combined_transcript: audioData.audio_analysis.combined_transcript || '',
            detected_language: audioData.audio_analysis.detected_language || 'unknown',
            speech_detected: audioData.audio_analysis.speech_detected || false,
            confidence: audioData.audio_analysis.confidence || 0,
            execution_time_ms: 0,
          }}));
          setAnalysisProgress(prev => ({ ...prev, audio: 'completed' }));
          console.log(`[@hook:useRestart] Step 2: Audio analysis completed`);
        } else {
          setAnalysisProgress(prev => ({ ...prev, audio: 'error' }));
          console.log(`[@hook:useRestart] Step 2: Audio analysis failed`);
        }
        
        // Step 3: Combined Subtitle + Summary Analysis (OPTIMIZED)
        console.log(`[@hook:useRestart] Step 3: Starting combined subtitle + summary analysis`);
        setAnalysisProgress(prev => ({ ...prev, subtitles: 'loading', summary: 'loading' }));
        
        const combinedResponse = await fetch(buildServerUrl('/server/restart/analyzeRestartComplete'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host,
            device_id: device.device_id || 'device1',
            video_id: videoData.video_id,
            screenshot_urls: videoData.screenshot_urls || [],
          }),
        });
        
        const combinedData = await combinedResponse.json();
        
        // Handle duplicate request (409) - treat as success since analysis is already running
        if (combinedResponse.status === 409 && combinedData.code === 'DUPLICATE_REQUEST') {
          console.log(`[@hook:useRestart] Step 3: Combined analysis already in progress, skipping`);
          setAnalysisProgress(prev => ({ ...prev, subtitles: 'completed', summary: 'completed' }));
        } else if (combinedData.success && combinedData.subtitle_analysis && combinedData.video_analysis) {
          // Update both subtitle and video description results from single response
          setAnalysisResults(prev => ({ 
            ...prev, 
            subtitles: {
              success: combinedData.subtitle_analysis.success,
              subtitles_detected: combinedData.subtitle_analysis.subtitles_detected || false,
              extracted_text: combinedData.subtitle_analysis.extracted_text || '',
              detected_language: combinedData.subtitle_analysis.detected_language || 'unknown',
              execution_time_ms: 0,
              frame_subtitles: combinedData.subtitle_analysis.frame_subtitles || [],
            },
            videoDescription: {
              frame_descriptions: combinedData.video_analysis.frame_descriptions || [],
              video_summary: combinedData.video_analysis.video_summary || '',
              frames_analyzed: combinedData.video_analysis.frames_analyzed || 0,
              execution_time_ms: 0,
            }
          }));
          setAnalysisProgress(prev => ({ ...prev, subtitles: 'completed', summary: 'completed' }));
          console.log(`[@hook:useRestart] Step 3: Combined analysis completed (subtitles + summary)`);
          
          // Show success toast for analysis completion - user can now see results!
          toast.showSuccess('✅ Analysis complete! Results available in settings.', { duration: 4000 });
          
          // Step 4: Generate Report in background (non-blocking)
          const reportKey = videoData.video_id;
          
          // Deduplication protection - prevent duplicate report generation
          if (isReportGenerationInProgress.current && currentReportVideoId.current === reportKey) {
            console.log(`[@hook:useRestart] Step 4: Report generation already in progress for ${reportKey}, ignoring duplicate request`);
            return;
          }
          
          // Mark report generation as in progress
          isReportGenerationInProgress.current = true;
          currentReportVideoId.current = reportKey;
          
          // Start report generation in background (don't await)
          generateReportInBackground(reportKey, videoData, audioData, combinedData);
        } else {
          setAnalysisProgress(prev => ({ ...prev, subtitles: 'error', summary: 'error', report: 'error' }));
          console.log(`[@hook:useRestart] Step 3: Combined analysis failed`);
        }
        
        console.log(`[@hook:useRestart] Core analysis steps completed - report generating in background`);
        
      } catch (analysisError) {
        // Handle AbortError separately (not a real error)
        if (analysisError instanceof Error && analysisError.name === 'AbortError') {
          console.log(`[@hook:useRestart] Analysis aborted (duplicate call prevention)`);
          return;
        }
        
        console.error(`[@hook:useRestart] Analysis error:`, analysisError);
        
        // Show error toast with timing if available
        if (analysisStartTime.current) {
          const analysisTime = Math.round((Date.now() - analysisStartTime.current) / 1000);
          toast.showError(`❌ AI Analysis failed after ${analysisTime}s`, { duration: 5000 });
        } else {
          toast.showError('❌ AI Analysis failed', { duration: 5000 });
        }
        
        // Don't fail the entire process if analysis fails - video is still playable
        setAnalysisProgress(prev => ({
          ...prev,
          audio: prev.audio === 'loading' ? 'error' : prev.audio,
          subtitles: prev.subtitles === 'loading' ? 'error' : prev.subtitles,
          summary: prev.summary === 'loading' ? 'error' : prev.summary,
          report: prev.report === 'loading' ? 'error' : prev.report,
        }));
      }

    } catch (err) {
      // Handle AbortError separately (not a real error)
      if (err instanceof Error && err.name === 'AbortError') {
        console.log(`[@hook:useRestart] Request aborted (duplicate call prevention)`);
        return;
      }
      
      const errorMessage = err instanceof Error ? err.message : 'Video generation failed';
      console.error('[@hook:useRestart] Video generation error:', errorMessage);
      toast.showError(`❌ ${errorMessage}`, { duration: 5000 });
      setError(errorMessage);
      setIsGenerating(false);
      setAnalysisProgress({ video: 'error', audio: 'idle', subtitles: 'idle', summary: 'idle', report: 'idle' });
    } finally {
      // Clean up request tracking
      isRequestInProgress.current = false;
    }
  }, [host, device, includeAudioAnalysis]);

  // =====================================================
  // EFFECTS
  // =====================================================

  // Auto-execute on mount only (React StrictMode protection)
  useEffect(() => {
    if (!hasExecutedOnMount.current) {
      hasExecutedOnMount.current = true;
      executeVideoGeneration();
    }
  }, []); // Empty dependency array - only run on mount

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isRequestInProgress.current = false;
    };
  }, []);

  // =====================================================
  // ANALYSIS FUNCTIONS
  // =====================================================

  // Screenshot analysis functions removed - backend provides comprehensive analysis

  // =====================================================
  // PUBLIC API FUNCTIONS
  // =====================================================

  const analyzeAudio = useCallback(async (_videoUrl: string) => {
    console.log('[@hook:useRestart] Audio analysis is handled by backend during video generation');
    return null;
  }, []);

  const analyzeSubtitles = useCallback(async (_imageUrl: string) => {
    console.log('[@hook:useRestart] Subtitle analysis is handled by backend during video generation');
    return null;
  }, []);

  const analyzeVideoDescription = useCallback(async (_imageUrl: string) => {
    console.log('[@hook:useRestart] Video description analysis is handled by backend during video generation');
    return null;
  }, []);

  const generateDubbedVersion = useCallback(async (language: string, transcript: string, videoId: string) => {
    const dubbingStartTime = Date.now();
    try {
      console.log(`[@hook:useRestart] 🎤 Starting dubbing generation for ${language}...`);
      setIsDubbing(true);
      
      const response = await fetch(buildServerUrl('/server/restart/generateDubbedVideo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id,
          video_id: videoId,
          target_language: language,
          existing_transcript: transcript
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        const dubbingDuration = ((Date.now() - dubbingStartTime) / 1000).toFixed(1);
        console.log(`[@hook:useRestart] ✅ Dubbing for ${language} completed in ${dubbingDuration}s`);
        
        setDubbedVideos(prev => ({
          ...prev,
          [language]: result.dubbed_video_url
        }));
        
        // Store audio URLs for comparison
        if (result.gtts_audio_url && result.edge_audio_url) {
          setDubbedAudioUrls(prev => ({
            ...prev,
            [language]: {
              gtts: result.gtts_audio_url,
              edge: result.edge_audio_url
            }
          }));
        }
      } else {
        throw new Error(result.error || 'Dubbing failed');
      }
    } catch (error) {
      console.error('Dubbing failed:', error);
      toast.showError('❌ Dubbing failed', { duration: 5000 });
    } finally {
      setIsDubbing(false);
    }
  }, [host, device, toast]);

  const translateToLanguage = useCallback(async (language: string) => {
    const translationStartTime = Date.now();
    try {
      setCurrentLanguage(language);
      
      if (language === 'en') {
        // Reset to original content for English
        return;
      }

      // Deduplication protection - prevent duplicate translation requests
      if (isTranslationInProgress.current && currentTranslationLanguage.current === language) {
        console.log(`[@hook:useRestart] Translation already in progress for ${language}, ignoring duplicate request`);
        return;
      }

      // Check cache first - if translation exists, use it immediately
      if (translationResults[language]) {
        console.log(`[@hook:useRestart] Using cached translation for ${language}`);
        return;
      }

      // Mark translation as in progress
      isTranslationInProgress.current = true;
      currentTranslationLanguage.current = language;
      setIsTranslating(true);
      
      console.log(`[@hook:useRestart] 🌐 Starting translation to ${language}...`);
      toast.showInfo(`🌐 Starting translation to ${language}...`, { duration: 3000 });

      // Prepare all content for single batch translation
      const contentBlocks = {
        video_summary: {
          text: analysisResults.videoDescription?.video_summary || '',
          source_language: 'en'
        },
        audio_transcript: {
          text: analysisResults.audio?.combined_transcript || '',
          source_language: analysisResults.audio?.detected_language?.toLowerCase() || 'en'
        },
        frame_descriptions: {
          texts: analysisResults.videoDescription?.frame_descriptions?.map(desc => {
            const descText = desc.includes(': ') ? desc.split(': ').slice(1).join(': ') : desc;
            return descText === 'No description available' ? '' : descText;
          }) || [],
          source_language: 'en'
        },
        frame_subtitles: {
          texts: analysisResults.subtitles?.frame_subtitles?.map(sub => {
            const subText = sub.includes(': ') ? sub.split(': ').slice(1).join(': ') : sub;
            return subText === 'No subtitles detected' ? '' : subText;
          }) || [],
          source_language: analysisResults.subtitles?.detected_language?.toLowerCase() || 'en'
        }
      };

      // Single API call for all translations
      const response = await fetch(buildServerUrl('/server/translate/restart-batch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_blocks: contentBlocks,
          target_language: language
        })
      });

      if (!response.ok) {
        throw new Error(`Batch translation API failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success && data.translations) {
        let newTranscript = '';
        let newSummary = '';
        let newFrameDescriptions: string[] = [];
        let newFrameSubtitles: string[] = [];

        // Apply all translations at once
        if (data.translations.video_summary) {
          newSummary = data.translations.video_summary;
        }
        
        if (data.translations.audio_transcript) {
          newTranscript = data.translations.audio_transcript;
        }
        
        if (data.translations.frame_descriptions && analysisResults.videoDescription?.frame_descriptions) {
          // Reconstruct with frame prefixes, maintaining exact 1:1 mapping
          newFrameDescriptions = analysisResults.videoDescription.frame_descriptions.map((originalDesc, index) => {
            const prefix = originalDesc.split(': ')[0];
            const originalText = originalDesc.includes(': ') ? originalDesc.split(': ').slice(1).join(': ') : originalDesc;
            
            // Use translated text if available and not empty, otherwise keep original
            const translatedText = data.translations.frame_descriptions[index];
            const finalText = (translatedText && translatedText.trim()) ? translatedText : originalText;
            
            return `${prefix}: ${finalText}`;
          });
        }
        
        if (data.translations.frame_subtitles && analysisResults.subtitles?.frame_subtitles) {
          // Reconstruct with frame prefixes, maintaining exact 1:1 mapping
          newFrameSubtitles = analysisResults.subtitles.frame_subtitles.map((originalSub, index) => {
            const prefix = originalSub.split(': ')[0];
            const originalText = originalSub.includes(': ') ? originalSub.split(': ').slice(1).join(': ') : originalSub;
            
            // Use translated text if available and not empty, otherwise keep original
            const translatedText = data.translations.frame_subtitles[index];
            const finalText = (translatedText && translatedText.trim()) ? translatedText : originalText;
            
            return `${prefix}: ${finalText}`;
          });
        }

        // Cache the results for future use
        setTranslationResults(prev => ({
          ...prev,
          [language]: {
            transcript: newTranscript,
            summary: newSummary,
            frameDescriptions: newFrameDescriptions,
            frameSubtitles: newFrameSubtitles,
          }
        }));
        
        const translationDuration = ((Date.now() - translationStartTime) / 1000).toFixed(1);
        console.log(`[@hook:useRestart] ✅ Translation to ${language} completed in ${translationDuration}s`);
        toast.showSuccess(`✅ Translation to ${language} complete! (${translationDuration}s)`, { duration: 4000 });
        
        // Auto-trigger dubbing after successful translation (if audio transcript available)
        if (analysisResults.audio?.combined_transcript && analysisResults.videoDescription) {
          const videoId = `restart_${Date.now()}`;
          const dubbingAutoStartTime = Date.now();
          console.log(`[@hook:useRestart] Auto-triggering dubbing for language: ${language}`);
          toast.showInfo(`🎤 Starting dubbing for ${language}...`, { duration: 3000 });
          
          try {
            await generateDubbedVersion(language, analysisResults.audio.combined_transcript, videoId);
            const totalDubbingDuration = ((Date.now() - dubbingAutoStartTime) / 1000).toFixed(1);
            console.log(`[@hook:useRestart] 🎬 Complete dubbing workflow for ${language} finished in ${totalDubbingDuration}s`);
            toast.showSuccess(`🎬 Dubbing for ${language} complete! (${totalDubbingDuration}s)`, { duration: 4000 });
          } catch (dubbingError) {
            console.error('[@hook:useRestart] Auto-dubbing failed:', dubbingError);
            toast.showError(`❌ Dubbing for ${language} failed`, { duration: 5000 });
          }
        } else {
          console.warn('[@hook:useRestart] Cannot auto-trigger dubbing - missing audio transcript or video data');
        }
        
      } else {
        throw new Error(data.error || 'Batch translation failed');
      }
      
    } catch (error) {
      console.error('[@hook:useRestart] Batch translation error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.showError(`❌ Translation failed: ${errorMessage}`, { duration: 5000 });
    } finally {
      setIsTranslating(false);
      // Clear deduplication flags
      isTranslationInProgress.current = false;
      currentTranslationLanguage.current = null;
    }
  }, [analysisResults, toast, generateDubbedVersion]);

  const applyAudioTiming = useCallback(async (offsetMs: number) => {
    if (offsetMs === 0) return; // No change needed
    
    try {
      setIsApplyingTiming(true);
      
      // Determine if we're working with dubbed or original video
      const isDubbed = currentLanguage !== 'en' && dubbedVideos[currentLanguage];
      const targetVideoUrl = isDubbed ? dubbedVideos[currentLanguage] : videoUrl;
      
      if (!targetVideoUrl) {
        throw new Error('No video available for timing adjustment');
      }
      
      const response = await fetch(buildServerUrl('/server/restart/adjustAudioTiming'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id,
          video_url: targetVideoUrl,
          timing_offset_ms: offsetMs,
          language: currentLanguage
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Update the appropriate video URL
        if (isDubbed) {
          setDubbedVideos(prev => ({ ...prev, [currentLanguage]: result.adjusted_video_url }));
        } else {
          setVideoUrl(result.adjusted_video_url);
        }
        setAudioTimingOffset(offsetMs);
        toast.showSuccess(`✅ Audio timing adjusted by ${offsetMs > 0 ? '+' : ''}${offsetMs}ms`);
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Audio timing adjustment failed:', error);
      toast.showError('❌ Audio timing adjustment failed');
    } finally {
      setIsApplyingTiming(false);
    }
  }, [host, device, videoUrl, dubbedVideos, currentLanguage, toast]);

  const regenerateVideo = useCallback(async () => {
    videoCache.delete(host, device);
    await executeVideoGeneration();
  }, [host, device, executeVideoGeneration]);

  // =====================================================
  // COMPUTED VALUES
  // =====================================================

  const isAnalysisComplete = useMemo(() => {
    if (!includeAudioAnalysis) return true;
    
    return analysisProgress.audio !== 'idle' && analysisProgress.audio !== 'loading' &&
           analysisProgress.subtitles !== 'idle' && analysisProgress.subtitles !== 'loading' &&
           analysisProgress.summary !== 'idle' && analysisProgress.summary !== 'loading';
  }, [analysisProgress, includeAudioAnalysis]);

  // =====================================================
  // RETURN API
  // =====================================================

  return {
    // Core video state
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
    reportUrl,
    
    // Analysis state
    analysisResults,
    analysisProgress,
    isAnalysisComplete,
    
    // Dubbing state
    dubbedVideos,
    dubbedAudioUrls,
    isDubbing,
    
    // Translation state
    translationResults,
    isTranslating,
    currentLanguage,
    
    // Manual analysis triggers
    analyzeAudio,
    analyzeSubtitles,
    analyzeVideoDescription,
    
    // Translation function
    translateToLanguage,
    
    // Dubbing function
    generateDubbedVersion,
    
    // Audio timing
    audioTimingOffset,
    isApplyingTiming,
    applyAudioTiming,
    
    // Utility functions
    regenerateVideo,
  };
};