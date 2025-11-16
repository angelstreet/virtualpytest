import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { Box, Typography, IconButton } from '@mui/material';
import React, { useRef, useEffect, useState, useCallback } from 'react';

import { StreamViewerLayoutConfig } from '../../config/layoutConfig';

interface HLSVideoPlayerProps {
  streamUrl?: string;
  isStreamActive?: boolean;
  isCapturing?: boolean;
  sx?: any;
  videoElementRef?: React.RefObject<HTMLVideoElement>;
  model?: string;
  layoutConfig?: StreamViewerLayoutConfig;
  isExpanded?: boolean;
  muted?: boolean; // Add muted prop
  isArchiveMode?: boolean; // Add archive mode prop
  shouldPause?: boolean; // Pause player to show last frame (during quality transition)
  onRestartRequest?: () => void; // Callback to expose restart functionality
  onPlayerReady?: () => void; // Callback when player loads successfully
  onCurrentSegmentChange?: (segmentUrl: string) => void; // Callback when current segment changes
}

/**
 * HLS Video Player Component
 *
 * Universal video player supporting both HLS streams and MP4 files.
 * Automatically detects format and uses appropriate playback method.
 *
 * Features:
 * - HLS live streaming with low latency configuration
 * - MP4 video playback for recorded content
 * - Native fallback for Safari
 * - Auto-retry with fallback logic
 * - User interaction handling for autoplay
 * - Robust error handling and recovery
 * - CPU-efficient latency correction (only when needed)
 */
export function HLSVideoPlayer({
  streamUrl,
  isStreamActive = false,
  isCapturing = false,
  sx = {},
  videoElementRef,
  model,
  layoutConfig,
  muted = true, // Default to muted for autoplay compliance
  isArchiveMode = false, // Default to live mode
  shouldPause = false, // Default to not paused
  onRestartRequest, // New prop for external restart trigger
  onPlayerReady, // Callback when player loads successfully
  onCurrentSegmentChange, // Callback when current segment changes
}: HLSVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<any>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [streamLoaded, setStreamLoaded] = useState(false);
  const [currentStreamUrl, setCurrentStreamUrl] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [requiresUserInteraction, setRequiresUserInteraction] = useState(false);
  const [useNativePlayer, setUseNativePlayer] = useState(false);
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [segmentFailureCount, setSegmentFailureCount] = useState(0);
  const [ffmpegStuck, setFfmpegStuck] = useState(false);
  const maxRetries = 5;
  const maxSegmentFailures = 10; // Stop after 10 consecutive segment failures
  const retryDelay = 6000;
  const lastInitTime = useRef<number>(0);

  // Add native HLS support detection
  const [supportsNativeHLS, setSupportsNativeHLS] = useState(false);

  useEffect(() => {
    console.log('[@component:HLSVideoPlayer] Component mounted with props:', {
      streamUrl,
      isStreamActive,
      isCapturing,
      model,
      layoutConfig,
      hasVideoRef: !!videoRef.current,
    });

    return () => {
      console.log('[@component:HLSVideoPlayer] Component unmounting');
    };
  }, []);



  useEffect(() => {
    if (videoElementRef && videoRef.current) {
      (videoElementRef as any).current = videoRef.current;
    }
  }, [videoElementRef]);

  // Add effect for detecting native HLS support
  useEffect(() => {
    const tempVideo = document.createElement('video');
    setSupportsNativeHLS(tempVideo.canPlayType('application/vnd.apple.mpegurl') !== '');
  }, []);

  const cleanupStream = useCallback(() => {
    console.log('[@component:HLSVideoPlayer] Starting aggressive stream cleanup');
    
    // Clean up native playback event listeners first
    if (videoRef.current && nativePlaybackHandlersRef.current) {
      const video = videoRef.current;
      const handlers = nativePlaybackHandlersRef.current;
      
      video.removeEventListener('loadedmetadata', handlers.loadedmetadata);
      video.removeEventListener('error', handlers.error);
      video.removeEventListener('canplay', handlers.canplay);
      
      nativePlaybackHandlersRef.current = null;
      console.log('[@component:HLSVideoPlayer] Native playback event listeners removed during cleanup');
    }
    
    if (hlsRef.current) {
      try {
        // More aggressive HLS cleanup
        const hls = hlsRef.current;
        
        // Stop loading and detach media first
        hls.stopLoad();
        
        // Remove all event listeners to prevent callbacks
        hls.removeAllListeners();
        
        // Detach media source
        if (videoRef.current) {
          hls.detachMedia();
        }
        
        // Finally destroy the instance
        hls.destroy();
        
        console.log('[@component:HLSVideoPlayer] HLS instance destroyed successfully');
      } catch (error) {
        console.warn('[@component:HLSVideoPlayer] Error destroying HLS instance:', error);
      }
      hlsRef.current = null;
    }

    if (videoRef.current) {
      const video = videoRef.current;
      
      // Pause and clear video
      video.pause();
      
      // Remove all event listeners from video element
      video.removeAttribute('src');
      video.removeAttribute('srcObject');
      
      // Clear any media source
      if (video.srcObject) {
        video.srcObject = null;
      }
      
      // Force reload to clear any cached data
      video.load();
      
      console.log('[@component:HLSVideoPlayer] Video element cleaned up');
    }

    // Reset all state
    setStreamLoaded(false);
    setStreamError(null);
    setSegmentFailureCount(0);
    setFfmpegStuck(false);
    setCurrentStreamUrl(null);
    
    console.log('[@component:HLSVideoPlayer] Stream cleanup completed');
  }, []);

  const attemptPlay = useCallback(() => {
    if (!videoRef.current) return;

    const playPromise = videoRef.current.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn('[@component:HLSVideoPlayer] Autoplay failed:', err.message);
        if (err.name === 'NotAllowedError' || err.message.includes('user interaction')) {
          setRequiresUserInteraction(true);
        } else {
          console.warn('[@component:HLSVideoPlayer] Play failed, but continuing:', err.message);
        }
      });
    }
  }, []);

  const handleUserPlay = useCallback(() => {
    setRequiresUserInteraction(false);
    attemptPlay();
  }, [attemptPlay]);

  const nativePlaybackHandlersRef = useRef<{
    loadedmetadata: () => void;
    error: (e: any) => void;
    canplay: () => void;
  } | null>(null);

  const cleanupNativePlayback = useCallback(() => {
    if (videoRef.current && nativePlaybackHandlersRef.current) {
      const video = videoRef.current;
      const handlers = nativePlaybackHandlersRef.current;
      
      video.removeEventListener('loadedmetadata', handlers.loadedmetadata);
      video.removeEventListener('error', handlers.error);
      video.removeEventListener('canplay', handlers.canplay);
      
      nativePlaybackHandlersRef.current = null;
      console.log('[@component:HLSVideoPlayer] Native playback event listeners removed');
    }
  }, []);

  const tryNativePlayback = useCallback(async () => {
    if (!streamUrl || !videoRef.current) return false;

    // Prevent native attempt if not supported and not MP4
    if (!supportsNativeHLS && !streamUrl.includes('.mp4')) {
      console.warn('[@component:HLSVideoPlayer] Native playback not supported for this stream type');
      setStreamError('Browser does not support native playback for this stream');
      return false;
    }

    console.log('[@component:HLSVideoPlayer] Trying native HTML5 playback');
    setUseNativePlayer(true);

    try {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }

      // Clean up previous native playback handlers if any
      cleanupNativePlayback();

      const video = videoRef.current;

      const handleLoadedMetadata = () => {
        console.log('[@component:HLSVideoPlayer] Native playback loaded successfully');
        setStreamLoaded(true);
        setStreamError(null); // Clear any existing errors
        setRetryCount(0);
        onPlayerReady?.(); // Notify parent that player is ready
        attemptPlay();
      };

      const handleError = (e: any) => {
        const target = e.target as HTMLVideoElement;
        const mediaError = target?.error;
        
        console.warn('[@component:HLSVideoPlayer] Native playback error:', {
          event: e,
          mediaError,
          code: mediaError?.code,
          message: mediaError?.message,
        });
        
        // Mark stream as failed
        setStreamLoaded(false);
        setStreamError('Stream playback error. Retrying...');
        
        // Trigger retry mechanism only if stream is still active
        if (isStreamActive) {
          setTimeout(() => {
            setRetryCount((prev) => prev + 1);
          }, retryDelay);
        } else {
          console.log('[@component:HLSVideoPlayer] Skipping retry - stream is paused (isStreamActive=false)');
        }
      };

      const handleCanPlay = () => {
        setStreamLoaded(true);
        setStreamError(null); // Clear any existing errors
        onPlayerReady?.(); // Notify parent that player is ready
      };

      // Store handlers for cleanup
      nativePlaybackHandlersRef.current = {
        loadedmetadata: handleLoadedMetadata,
        error: handleError,
        canplay: handleCanPlay,
      };

      video.addEventListener('loadedmetadata', handleLoadedMetadata);
      video.addEventListener('error', handleError);
      video.addEventListener('canplay', handleCanPlay);

      video.src = streamUrl + (streamUrl.includes('?') ? '&' : '?') + 't=' + Date.now();
      video.load();

      return true;
    } catch (error) {
      console.error('[@component:HLSVideoPlayer] Native playback setup failed:', error);
      return false;
    }
  }, [streamUrl, attemptPlay, cleanupNativePlayback, supportsNativeHLS, isStreamActive, retryDelay]);

  const initializeStream = useCallback(async () => {
    // Skip if stream is intentionally paused (e.g., modal closed, background player paused)
    if (!isStreamActive) {
      console.log('[@component:HLSVideoPlayer] Skipping init - stream is paused (isStreamActive=false)');
      return;
    }

    // Don't initialize if FFmpeg is stuck - requires external intervention
    if (ffmpegStuck) {
      console.warn('[@component:HLSVideoPlayer] FFmpeg is stuck, refusing to initialize stream');
      return;
    }

    const now = Date.now();
    if (now - lastInitTime.current < 1000) {
      console.log(
        '[@component:HLSVideoPlayer] Throttling initialization, too soon since last attempt',
      );
      return;
    }
    lastInitTime.current = now;

    if (!streamUrl || !videoRef.current) {
      setStreamError('Stream URL or video element not available');
      return;
    }

    // Skip if we're already initialized with the same URL and stream is loaded
    if (currentStreamUrl === streamUrl && streamLoaded && !streamError) {
      console.log(
        '[@component:HLSVideoPlayer] Stream already loaded with same URL, skipping initialization',
      );
      return;
    }

    setStreamError(null);
    setStreamLoaded(false);
    setRequiresUserInteraction(false);
    setSegmentFailureCount(0);
    setFfmpegStuck(false);

    // Check if this is an MP4 file (recorded video)
    if (streamUrl.includes('.mp4')) {
      console.log('[@component:HLSVideoPlayer] Detected MP4 file, using native playback');
      const nativeSuccess = await tryNativePlayback();
      if (nativeSuccess) return;
    }

    if (retryCount >= 2 && supportsNativeHLS || useNativePlayer) {
      const nativeSuccess = await tryNativePlayback();
      if (nativeSuccess) return;
    }

    try {
      console.log('[@component:HLSVideoPlayer] Initializing HLS stream:', streamUrl);

      // If HLS instance exists and URL changed, just reload source (safer than destroy/recreate)
      if (hlsRef.current && currentStreamUrl !== streamUrl) {
        console.log('[@component:HLSVideoPlayer] Reloading source without destroying HLS instance');
        console.log('[@component:HLSVideoPlayer] Old URL:', currentStreamUrl);
        console.log('[@component:HLSVideoPlayer] New URL:', streamUrl);
        setCurrentStreamUrl(streamUrl);
        setStreamLoaded(false); // Mark as not loaded during transition
        hlsRef.current.stopLoad();
        hlsRef.current.detachMedia();
        hlsRef.current.loadSource(streamUrl);
        hlsRef.current.attachMedia(videoRef.current);
        // The existing MANIFEST_PARSED handler will fire and call onPlayerReady
        console.log('[@component:HLSVideoPlayer] Source reloaded, waiting for manifest parse...');
        return;
      }

      // Full cleanup only if no HLS instance yet
      if (hlsRef.current) {
        cleanupStream();
      }

      setCurrentStreamUrl(streamUrl);

      const HLSModule = await import('hls.js');
      const HLS = HLSModule.default;

      if (!HLS.isSupported()) {
        console.log('[@component:HLSVideoPlayer] HLS.js not supported, using native playback');
        await tryNativePlayback();
        return;
      }

      // Dynamic HLS configuration based on mode
      const hlsConfig = isArchiveMode ? {
        // Archive mode - optimized for seeking and timeline navigation
        enableWorker: false,
        lowLatencyMode: false,         // Disable low latency for archive
        // Note: liveSyncDuration and liveMaxLatencyDuration omitted for archive mode
        // to avoid validation errors and let HLS.js use defaults
        maxBufferLength: 30,           // Larger buffer for smooth seeking
        maxMaxBufferLength: 60,        // Allow more buffering
        backBufferLength: 30,          // Keep back buffer for seeking
        maxBufferSize: 10 * 1000 * 1000, // Larger buffer size
        maxBufferHole: 2,              // More tolerance for gaps
        fragLoadingTimeOut: 10000,     // More time for fragment loading
        manifestLoadingTimeOut: 30000, // 30s timeout for large 24h manifests
        levelLoadingTimeOut: 30000,    // 30s timeout for large manifests
        liveBackBufferLength: 30,      // Keep back buffer
        liveDurationInfinity: false,   // Finite duration for archive
      } : {
        // Live mode - aggressive live edge with background buffering for 150s scrubbing
        enableWorker: false,
        lowLatencyMode: true,          // ✅ Enable aggressive live edge targeting
        liveSyncDuration: 1,           // Target 1s behind live edge
        liveMaxLatencyDuration: 5,     // ✅ Force back to live if drift >5s (was 180s)
        maxBufferLength: 10,           // ✅ Load only 10s initially for fast startup (was 150s)
        maxMaxBufferLength: 150,       // But ALLOW up to 150s total as buffer fills
        backBufferLength: 150,         // Keep 150s for scrubbing (fills backward in background)
        maxBufferSize: 15 * 1000 * 1000, // 15MB for full 150s buffer
        maxBufferHole: 0.1,            // Fill gaps faster
        fragLoadingTimeOut: 5000,      // Fail faster
        manifestLoadingTimeOut: 3000,  // Fail faster
        levelLoadingTimeOut: 3000,     // Fail faster
        liveBackBufferLength: 150,     // ✅ Continue loading old segments backward (150s scrubbing)
        liveDurationInfinity: true,    // Allow infinite live duration
      };

      const hls = new HLS(hlsConfig);

      hlsRef.current = hls;

      hls.on(HLS.Events.MANIFEST_PARSED, () => {
        console.log('[@component:HLSVideoPlayer] HLS manifest parsed successfully');
        setStreamLoaded(true);
        setStreamError(null); // Clear any existing errors
        setRetryCount(0);
        setSegmentFailureCount(0); // Reset segment failure count on successful manifest parse
        onPlayerReady?.(); // Notify parent that player is ready
        setFfmpegStuck(false); // Reset FFmpeg stuck state
        attemptPlay();
      });

      // Reset segment failure count on successful fragment loads
      hls.on(HLS.Events.FRAG_LOADED, (_event, data) => {
        setSegmentFailureCount(0);
        // Clear any existing error messages when fragments load successfully (indicates recovery)
        setStreamError((prev) => {
          if (prev) {
            console.log('[@component:HLSVideoPlayer] Stream recovered, clearing error message');
            return null;
          }
          return prev;
        });
        
        // Notify parent of current segment URL for screenshot/capture alignment
        if (data.frag?.url && onCurrentSegmentChange) {
          onCurrentSegmentChange(data.frag.url);
        }
      });

      // Latency correction removed - allow users to scrub back without auto-correction

      hls.on(HLS.Events.ERROR, (_event, data) => {
        // Ignore buffer-related errors and transient network timeouts - they are temporary and self-recovering
        if (data.details === 'bufferStalledError' || 
            data.details === 'bufferSeekOverHole' || 
            data.details === 'bufferNudgeOnStall' ||
            data.details === 'levelLoadTimeOut') {
          // Silently ignore these - they are normal HLS.js recovery mechanisms
          return;
        }

        console.warn('[@component:HLSVideoPlayer] HLS error:', data.type, data.details, data.fatal, data);

        // Check for segment loading failures (404 errors indicating FFmpeg stuck)
        if (data.details === 'fragLoadError' && data.response?.code === 404) {
          setSegmentFailureCount((prev) => {
            // Don't increment if already at max - prevents counter from going beyond threshold
            if (prev >= maxSegmentFailures) {
              return prev;
            }
            
            const newCount = prev + 1;
            console.warn(`[@component:HLSVideoPlayer] Segment 404 error (${newCount}/${maxSegmentFailures}):`, data.frag?.url);
            
            if (newCount >= maxSegmentFailures) {
              console.error('[@component:HLSVideoPlayer] FFmpeg appears stuck - too many consecutive segment failures');
              setFfmpegStuck(true);
              setStreamError('FFmpeg appears stuck. Stream restart required.');
              
              // Immediately cleanup HLS instance to stop further attempts
              setTimeout(() => {
                if (hlsRef.current) {
                  try {
                    hlsRef.current.destroy();
                    hlsRef.current = null;
                  } catch (error) {
                    console.warn('[@component:HLSVideoPlayer] Error destroying HLS on FFmpeg stuck:', error);
                  }
                }
              }, 100);
              
              return newCount;
            }
            
            return newCount;
          });
          
          // Don't attempt recovery for segment failures - let them accumulate
          return;
        }

        // Reset segment failure count on successful operations or different error types
        if (data.details !== 'fragLoadError') {
          setSegmentFailureCount(0);
        }

        if (data.fatal) {
          console.error('[@component:HLSVideoPlayer] Fatal HLS error, trying recovery');

          // If stream is paused, never attempt fatal recovery (e.g. background preview while modal is open)
          if (!isStreamActive) {
            console.log('[@component:HLSVideoPlayer] Skipping fatal recovery - stream is paused (isStreamActive=false)');
            return;
          }

          // Special case: manifest 404 -> treat as terminal and stop retrying
          if (
            data.type === 'networkError' &&
            data.details === 'manifestLoadError' &&
            data.response?.code === 404
          ) {
            console.warn('[@component:HLSVideoPlayer] Manifest 404 - stopping retries and cleaning up');
            setStreamError('Stream manifest not found (404). Stream is unavailable.');
            // Clean up HLS instance to stop further requests
            cleanupStream();
            return;
          }

          if (supportsNativeHLS) {
            setUseNativePlayer(true);
            setTimeout(() => {
              // Only try native playback if stream is still active
              if (isStreamActive) {
                tryNativePlayback();
              } else {
                console.log('[@component:HLSVideoPlayer] Skipping native retry after fatal error - stream paused');
              }
            }, 500);
          } else {
            console.log('[@component:HLSVideoPlayer] Restarting HLS after fatal error (non-native browser)');
            cleanupStream();
            setTimeout(() => {
              if (!isStreamActive) {
                console.log('[@component:HLSVideoPlayer] Skipping HLS restart after fatal error - stream paused');
                return;
              }
              setRetryCount(0);
              initializeStream();
            }, retryDelay);
          }
        } else {
          if (data.details === 'fragParsingError' || data.details === 'fragLoadError') {
            // Only attempt recovery if not stuck and not a 404 error
            if (!ffmpegStuck && !(data.details === 'fragLoadError' && data.response?.code === 404)) {
              console.log('[@component:HLSVideoPlayer] Fragment error, attempting HLS recovery');
              try {
                hls.startLoad();
              } catch (recoveryError) {
                console.warn('[@component:HLSVideoPlayer] HLS recovery failed:', recoveryError);
                setStreamError('Stream connection issues. Retrying...');
                setTimeout(() => {
                  setRetryCount((prev) => prev + 1);
                }, retryDelay);
              }
            }
          } else {
            setStreamError('Stream connection issues. Retrying...');
          }
        }
      });

      hls.loadSource(streamUrl);
      hls.attachMedia(videoRef.current);
    } catch (error: any) {
      console.error('[@component:HLSVideoPlayer] Stream initialization failed:', error);
      setStreamError(`Stream initialization failed: ${error.message}`);
      setTimeout(() => {
        setRetryCount((prev) => prev + 1);
      }, retryDelay);
    }
  }, [streamUrl, retryCount, useNativePlayer, currentStreamUrl, cleanupStream, tryNativePlayback, ffmpegStuck, supportsNativeHLS]);

  // Manual restart handler - clears all errors and reinitializes stream
  const handleManualRestart = useCallback(() => {
    console.log('[@component:HLSVideoPlayer] Manual restart triggered');
    // Reset all error states
    setStreamError(null);
    setSegmentFailureCount(0);
    setFfmpegStuck(false);
    setRetryCount(0);
    setStreamLoaded(false);
    setUseNativePlayer(false);
    
    // Cleanup current stream
    cleanupStream();
    
    // Reinitialize after cleanup
    setTimeout(() => {
      initializeStream();
    }, 300);
  }, [cleanupStream, initializeStream]);

  // Expose restart handler to parent via callback
  useEffect(() => {
    if (onRestartRequest) {
      // Store the restart handler so parent can call it
      (onRestartRequest as any).current = handleManualRestart;
    }
  }, [onRestartRequest, handleManualRestart]);

  const handleStreamError = useCallback(() => {
    // Don't retry if stream is paused
    if (!isStreamActive) {
      console.log('[@component:HLSVideoPlayer] Skipping retry - stream is paused (isStreamActive=false)');
      return;
    }

    // Don't retry if FFmpeg is stuck - requires external intervention
    if (ffmpegStuck) {
      console.warn('[@component:HLSVideoPlayer] FFmpeg stuck, not retrying - requires stream restart');
      return;
    }

    if (retryCount >= maxRetries) {
      console.warn('[@component:HLSVideoPlayer] Max retries reached, switching to native playback');
      setUseNativePlayer(true);
      setTimeout(() => tryNativePlayback(), 1000);
      return;
    }

    console.log(
      `[@component:HLSVideoPlayer] Stream error, retrying in ${retryDelay}ms (attempt ${retryCount + 1}/${maxRetries})`,
    );

    setTimeout(() => {
      setRetryCount((prev) => {
        const newCount = prev + 1;
        console.log(`[@component:HLSVideoPlayer] Incrementing retry count: ${prev} -> ${newCount}`);
        return newCount;
      });
      initializeStream();
    }, retryDelay);
  }, [retryCount, maxRetries, retryDelay, initializeStream, tryNativePlayback, ffmpegStuck, isStreamActive]);

  useEffect(() => {
    // Don't retry if FFmpeg is stuck or stream is paused
    if (streamError && retryCount < maxRetries && !ffmpegStuck && isStreamActive) {
      console.log(
        `[@component:HLSVideoPlayer] Stream error detected, current retry count: ${retryCount}/${maxRetries}`,
      );
      // Only auto-retry if stream is not loaded (avoid retrying transient errors on working stream)
      if (!streamLoaded) {
        handleStreamError();
      }
    } else if (streamError && (retryCount >= maxRetries || ffmpegStuck)) {
      console.warn(
        `[@component:HLSVideoPlayer] ${ffmpegStuck ? 'FFmpeg stuck' : `Max retries (${maxRetries}) reached`}, stopping retry attempts`,
      );
    } else if (streamError && !isStreamActive) {
      console.log('[@component:HLSVideoPlayer] Stream error exists but stream is paused - not retrying');
    }
  }, [streamError, retryCount, maxRetries, streamLoaded, ffmpegStuck, isStreamActive, handleStreamError]);

  useEffect(() => {
    if (useNativePlayer && streamUrl && isStreamActive) {
      tryNativePlayback();
    }
  }, [useNativePlayer, streamUrl, isStreamActive, tryNativePlayback]);

  // Initialization - only on streamUrl change
  // Use refs to track current URL to avoid circular dependencies
  const currentStreamUrlRef = useRef<string | null>(null);
  
  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;

    // Don't initialize during quality switching - wait for polling to complete
    if (shouldPause) {
      console.log('[@component:HLSVideoPlayer] Skipping init - quality switch in progress (shouldPause=true)');
      return;
    }

    // Only initialize if URL actually changed
    if (currentStreamUrlRef.current === streamUrl) {
      console.log('[@component:HLSVideoPlayer] Skipping init - same URL, already initialized');
      return;
    }

    console.log('[@component:HLSVideoPlayer] URL changed - initializing:', streamUrl);
    // Reset error states but don't cleanup (preserve if possible)
    setStreamError(null);
    setRetryCount(0);
    setSegmentFailureCount(0);
    setFfmpegStuck(false);
    setStreamLoaded(false);
    setCurrentStreamUrl(streamUrl);
    currentStreamUrlRef.current = streamUrl;

    initializeStream(); // Initialize without destructive cleanup
  }, [streamUrl, shouldPause, initializeStream]); // Depend on external props and the init callback

  // Handle shouldPause prop - pause to show last frame (e.g., during quality transition)
  const prevShouldPause = useRef(shouldPause);
  useEffect(() => {
    if (!videoRef.current) return;

    const shouldPauseChanged = prevShouldPause.current !== shouldPause;
    prevShouldPause.current = shouldPause;

    if (shouldPause) {
      console.log('[@component:HLSVideoPlayer] Quality switch started - pausing and preventing init');
      if (streamLoaded) {
        videoRef.current.pause();
      }
    } else if (shouldPauseChanged && streamUrl && isStreamActive) {
      // Only reinitialize when shouldPause changes from true to false (quality switch completes)
      console.log('[@component:HLSVideoPlayer] Quality switch complete (shouldPause changed from true to false) - initializing stream');
      setStreamLoaded(false);
      setStreamError(null);
      initializeStream();
    }
  }, [shouldPause, streamUrl, isStreamActive, streamLoaded, initializeStream]);

  // Pause/resume - non-destructive
  useEffect(() => {
    if (!hlsRef.current || !videoRef.current || !streamLoaded) return;

    if (isStreamActive) {
      console.log('[@component:HLSVideoPlayer] Resuming stream (non-destructive)');
      hlsRef.current.startLoad();
      attemptPlay();
    } else {
      console.log('[@component:HLSVideoPlayer] Pausing stream (non-destructive)');
      hlsRef.current.stopLoad();
      videoRef.current.pause();
    }
  }, [isStreamActive, streamLoaded, attemptPlay]);

  // Simplified video ready check - no polling needed
  useEffect(() => {
    const ready = !!videoRef.current;
    if (ready !== isVideoReady) {
      setIsVideoReady(ready);
      console.log('[@component:HLSVideoPlayer] Video ready state changed:', ready);
    }
  }, [streamLoaded, isVideoReady]);

  // Dedicated cleanup effect for component unmount - always runs
  useEffect(() => {
    return () => {
      console.log('[@component:HLSVideoPlayer] Final unmount cleanup');
      cleanupStream();
    };
  }, []); // Empty dependency array - only runs on mount/unmount

  // Add visibility change handler for recovery
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        return;
      }

      console.log('[@component:HLSVideoPlayer] Tab became visible');
      if (!streamUrl || !isStreamActive) return;

      if (streamError || !streamLoaded || ffmpegStuck) {
        console.log('[@component:HLSVideoPlayer] Restarting stream on visibility change');
        handleManualRestart();
        return;
      }

      if (videoRef.current?.paused) {
        attemptPlay();
      }

      // Latency correction removed - allow users to stay at their chosen position
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [streamUrl, isStreamActive, streamError, streamLoaded, ffmpegStuck, handleManualRestart, attemptPlay, isArchiveMode]);

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        ...sx,
      }}
    >
            <video
        ref={videoRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: layoutConfig?.objectFit || 'contain',
          aspectRatio: layoutConfig?.aspectRatio,
          minHeight: layoutConfig?.minHeight,
          backgroundColor: '#000000',
          // Hide video during quality switch to prevent corrupted frames from showing
          display: streamLoaded && !shouldPause ? 'block' : 'none',
        }}
        autoPlay
        playsInline
        muted={muted}
        draggable={false}
        preload="none"
        crossOrigin="anonymous"
      />

      {streamError && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: 'white',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            padding: 2,
            borderRadius: 1,
            zIndex: 10,
          }}
        >
          <Typography variant="body2" sx={{ mb: 1 }}>
            {streamError}
          </Typography>
          {ffmpegStuck ? (
            <Typography variant="caption" color="error.main">
              Segment failures: {segmentFailureCount}/{maxSegmentFailures}
            </Typography>
          ) : (
            <Typography variant="caption" color="text.secondary">
              Retry {retryCount}/{maxRetries}
            </Typography>
          )}
        </Box>
      )}

      {!streamLoaded && !streamError && streamUrl && isStreamActive && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: 'white',
            zIndex: 10,
          }}
        >
          <Typography variant="body2">Loading stream...</Typography>
        </Box>
      )}

      {requiresUserInteraction && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: 'white',
            zIndex: 20,
          }}
        >
          <IconButton
            onClick={handleUserPlay}
            sx={{
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
              },
            }}
            size="large"
          >
            <PlayArrowIcon fontSize="large" />
          </IconButton>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Click to play
          </Typography>
        </Box>
      )}
    </Box>
  );
}
