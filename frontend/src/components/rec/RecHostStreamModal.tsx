import { Box } from '@mui/material';
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';

import { VNCStateProvider } from '../../contexts/VNCStateContext';
import { useStream } from '../../hooks/controller';
import { useRec } from '../../hooks/pages/useRec';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import { useToast } from '../../hooks/useToast';
import { useMonitoring } from '../../hooks/monitoring/useMonitoring';
import { Host, Device } from '../../types/common/Host_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { buildServerUrl, buildCaptureUrl } from '../../utils/buildUrlUtils';
import { AIExecutionPanel } from '../ai';
import { PromptDisambiguation } from '../ai/PromptDisambiguation';

import { RecStreamModalHeader } from './RecStreamModalHeader';
import { RecStreamContainer } from './RecStreamContainer';
import { RecPanelManager } from './RecPanelManager';

interface RecHostStreamModalProps {
  host: Host;
  device?: Device;
  isOpen: boolean;
  onClose: () => void;
  showRemoteByDefault?: boolean;
  sharedVideoRef?: React.RefObject<HTMLVideoElement>;
}

export const RecHostStreamModal: React.FC<RecHostStreamModalProps> = ({
  host,
  device,
  isOpen,
  onClose,
  showRemoteByDefault = false,
  sharedVideoRef,
}) => {
  if (!isOpen || !host) return null;

  return (
    <VNCStateProvider>
      <RecHostStreamModalContent
        host={host}
        device={device}
        onClose={onClose}
        showRemoteByDefault={showRemoteByDefault}
        sharedVideoRef={sharedVideoRef}
      />
    </VNCStateProvider>
  );
};

const RecHostStreamModalContent: React.FC<{
  host: Host;
  device?: Device;
  onClose: () => void;
  showRemoteByDefault: boolean;
  sharedVideoRef?: React.RefObject<HTMLVideoElement>;
}> = ({ host, device, onClose, showRemoteByDefault, sharedVideoRef }) => {
  // Local state
  const [showRemote, setShowRemote] = useState<boolean>(showRemoteByDefault);
  const [showWeb, setShowWeb] = useState<boolean>(false);
  const [monitoringMode, setMonitoringMode] = useState<boolean>(false);
  const [aiAgentMode, setAiAgentMode] = useState<boolean>(false);
  const [restartMode, setRestartMode] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(true); // Start muted by default
  const [, setIsStreamActive] = useState<boolean>(true); // Stream lifecycle management
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true); // Start in live mode
  const [currentQuality, setCurrentQuality] = useState<'low' | 'sd' | 'hd'>('low'); // Start with LOW quality
  const currentQualityRef = useRef<'low' | 'sd' | 'hd'>('low'); // Ref to track quality for cleanup
  const [isQualitySwitching, setIsQualitySwitching] = useState<boolean>(false); // Track quality transition state
  const [shouldPausePlayer, setShouldPausePlayer] = useState<boolean>(false); // Pause player during transition
  const [currentVideoTime, setCurrentVideoTime] = useState<number>(0); // Track video currentTime for archive monitoring
  const pollingIntervalRef = useRef<NodeJS.Timeout | (() => void) | null>(null);
  // Throttle frequent video time updates to avoid excessive re-renders
  const lastVideoTimeUpdateRef = useRef<number>(0);
  const lastVideoTimeValueRef = useRef<number>(-1);
  
  // AI Disambiguation state and handlers
  const [disambiguationData, setDisambiguationData] = useState<any>(null);
  const [disambiguationResolve, setDisambiguationResolve] = useState<((selections: Record<string, string>, saveToDb: boolean) => void) | null>(null);
  const [disambiguationCancel, setDisambiguationCancel] = useState<(() => void) | null>(null);

  // Handler for disambiguation data changes from AIExecutionPanel
  const handleDisambiguationDataChange = useCallback((
    data: any,
    resolve: (selections: Record<string, string>, saveToDb: boolean) => void,
    cancel: () => void
  ) => {
    setDisambiguationData(data);
    setDisambiguationResolve(() => resolve);
    setDisambiguationCancel(() => cancel);
  }, []);

  // Hooks - now only run when modal is actually open
  const { showError, showWarning } = useToast();

  // Get VNC scaling for monitoring
  const { calculateVncScaling, pollForFreshStream } = useRec();

  // NEW: Use device control hook (replaces all duplicate control logic)
  const { isControlActive, isControlLoading, controlError, handleToggleControl, clearError } =
    useDeviceControl({
      host,
      device_id: device?.device_id || 'device1',
      sessionId: 'rec-stream-modal-session',
      autoCleanup: true, // Auto-release on unmount
    });

  // Use new stream hook - auto-fetches when host/device_id changes
  const { streamUrl, isLoadingUrl, urlError } = useStream({
    host,
    device_id: device?.device_id || 'device1',
  });

  // Use monitoring hook (polls every 500ms when monitoring mode is active)
  const monitoringData = useMonitoring({
    host,
    device,
    enabled: monitoringMode, // Only poll when monitoring is ON
    archiveMode: !isLiveMode, // Archive mode when in Last 24h
    currentVideoTime: currentVideoTime, // Current video time for archive lookup
  });

  // Stable stream container dimensions to prevent re-renders
  const streamContainerDimensions = useMemo(() => {
    // Only calculate when window is available
    if (typeof window === 'undefined') {
      console.log('[@RecHostStreamModal] Window not available, skipping dimension calculation');
      return { width: 0, height: 0, x: 0, y: 0 };
    }

    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    // Modal dimensions (95vw x 90vh)
    const modalWidth = windowWidth * 0.95;
    const modalHeight = windowHeight * 0.9;

    // Header height calculation based on actual Box styling
    const headerMinHeight = 48; // minHeight from header Box
    const headerPadding = 16; // py: 1 = 8px top + 8px bottom = 16px total
    const actualHeaderHeight = headerMinHeight + headerPadding; // 48 + 16 = 64px

    // Use fixed stream area (mobile overlay always shows with remote panel = 20%)
    const streamAreaWidth = modalWidth * 0.80;
    const streamAreaHeight = modalHeight - actualHeaderHeight;

    // Modal position (centered)
    const modalX = (windowWidth - modalWidth) / 2;
    const modalY = (windowHeight - modalHeight) / 2;

    // Stream container position calculation
    const streamX = modalX;
    
    // Calculate stream Y position - this should be the actual content area position
    // The content area starts immediately after the header (including padding)
    // Additional 32px offset needed for proper overlay alignment (empirically determined)
    const additionalOffset = 32; // Modal container padding/spacing not accounted for in CSS calculations
    const streamY = modalY + actualHeaderHeight + additionalOffset;

    const dimensions = {
      width: Math.round(streamAreaWidth),
      height: Math.round(streamAreaHeight),
      x: Math.round(streamX),
      y: Math.round(streamY),
    };

    console.log('[@RecHostStreamModal] Stream container dimensions calculated:', {
      windowSize: { width: windowWidth, height: windowHeight },
      modalSize: { width: modalWidth, height: modalHeight },
      modalPosition: { x: modalX, y: modalY },
      headerHeight: actualHeaderHeight,
      additionalOffset: additionalOffset,
      streamPosition: { x: streamX, y: streamY },
      finalDimensions: dimensions,
    });

    return dimensions;
  }, []);

  // Force recalculation after mount when window is available
  const [isWindowReady, setIsWindowReady] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsWindowReady(true);
    }
  }, []);

  // Recalculate dimensions when window becomes available
  const finalStreamContainerDimensions = useMemo(() => {
    if (!isWindowReady || typeof window === 'undefined') {
      return { width: 0, height: 0, x: 0, y: 0 };
    }
    return streamContainerDimensions;
  }, [streamContainerDimensions, isWindowReady]);

  // Check if this is a desktop device (host_vnc)
  const isDesktopDevice = useMemo(() => {
    return device?.device_model === 'host_vnc';
  }, [device?.device_model]);

  // Check if device has power control capability
  const hasPowerControl = useMemo(() => {
    // Check if device has power capability in its capabilities
    const capabilities = device?.device_capabilities;
    return capabilities && capabilities.power !== null && capabilities.power !== undefined;
  }, [device?.device_capabilities]);

  // Handle remote/terminal toggle
  const handleToggleRemote = useCallback(() => {
    if (!isControlActive) {
      showWarning('Please take control of the device first');
      return;
    }

    setShowRemote((prev) => !prev);
    console.log(
      `[@component:RecHostStreamModal] ${isDesktopDevice ? 'Terminal' : 'Remote'} panel toggled: ${!showRemote}`,
    );
  }, [isControlActive, showRemote, showWarning, isDesktopDevice]);

  // Handle web panel toggle
  const handleToggleWeb = useCallback(() => {
    if (!isControlActive) {
      showWarning('Please take control of the device first');
      return;
    }

    setShowWeb((prev) => {
      const newWeb = !prev;
      console.log(`[@component:RecHostStreamModal] Web panel toggled: ${newWeb}`);
      return newWeb;
    });
  }, [isControlActive, showWarning]);

  const handleToggleMonitoring = useCallback(() => {
    setMonitoringMode((prev) => {
      const newMode = !prev;
      console.log(`[@component:RecHostStreamModal] Monitoring toggled: ${newMode}`);

      if (newMode) {
        setAiAgentMode(false);
        setRestartMode(false);
        // AI analysis now only triggered on pause (live) or video time change (archive)
        console.log(`[@component:RecHostStreamModal] Monitoring enabled - AI analysis will trigger on pause (live) or time change (archive)`);
      }

      return newMode;
    });
  }, []);

  // Handle AI agent mode toggle
  const handleToggleAiAgent = useCallback(() => {
    if (!isControlActive) {
      showWarning('Please take control of the device first to enable AI agent');
      return;
    }

    setAiAgentMode((prev) => {
      const newMode = !prev;
      console.log(`[@component:RecHostStreamModal] AI agent mode toggled: ${newMode}`);

      // Disable monitoring mode and restart mode when enabling AI agent
      if (newMode) {
        setMonitoringMode(false);
        setRestartMode(false);
      }

      return newMode;
    });
  }, [isControlActive, showWarning]);

  // Handle restart mode toggle
  const handleToggleRestart = useCallback(() => {
    if (!isControlActive) {
      showWarning('Please take control of the device first to enable restart mode');
      return;
    }

    setRestartMode((prev) => {
      const newMode = !prev;
      console.log(`[@component:RecHostStreamModal] Restart mode toggled: ${newMode}`);

      // Disable monitoring mode and AI agent mode when enabling restart
      if (newMode) {
        setMonitoringMode(false);
        setAiAgentMode(false);
      }

      return newMode;
    });
  }, [isControlActive, showWarning]);

  // Handle live/24h mode toggle
  const handleToggleLiveMode = useCallback(() => {
    setIsLiveMode((prev) => {
      const newMode = !prev;
      console.log(`[@component:RecHostStreamModal] Live mode toggled: ${newMode ? 'Live' : 'Last 24h'}`);
      return newMode;
    });
  }, []);

  // Poll for new stream availability using hook function
  const pollForNewStream = useCallback((deviceId: string) => {
    console.log(`[@component:RecHostStreamModal] Starting polling for new stream using hook function`);
    
    const cleanup = pollForFreshStream(
      host,
      deviceId,
      // onReady callback
      () => {
        console.log(`[@component:RecHostStreamModal] ✅ Fresh stream ready from hook - hiding overlay`);
        setShouldPausePlayer(false);
        setIsQualitySwitching(false);
        // Clear the polling reference
        pollingIntervalRef.current = null;
      },
      // onTimeout callback
      (error: string) => {
        console.warn(`[@component:RecHostStreamModal] Polling timeout from hook - ${error}`);
        setShouldPausePlayer(false);
        setIsQualitySwitching(false);
        showWarning(error);
        // Clear the polling reference
        pollingIntervalRef.current = null;
      }
    );
    
    // Store cleanup function reference for manual cleanup if needed
    pollingIntervalRef.current = cleanup as any; // Store cleanup function instead of interval
  }, [host, pollForFreshStream, showWarning]);

  // Common function to switch quality (reused for initial entry and button clicks)
  const switchQuality = useCallback(async (targetQuality: 'low' | 'sd' | 'hd', showLoadingOverlay: boolean = true, isInitialLoad: boolean = false) => {
    console.log(`[@component:RecHostStreamModal] Switching to ${targetQuality.toUpperCase()} quality (showOverlay=${showLoadingOverlay}, isInitialLoad=${isInitialLoad})`);
    
    // Stop any existing polling
    if (pollingIntervalRef.current) {
      if (typeof pollingIntervalRef.current === 'function') {
        // New hook-based cleanup function
        pollingIntervalRef.current();
      } else {
        // Legacy interval cleanup (fallback)
        clearInterval(pollingIntervalRef.current);
      }
      pollingIntervalRef.current = null;
    }
    
    // Update state based on target quality
    setCurrentQuality(targetQuality);
    currentQualityRef.current = targetQuality; // Sync ref for cleanup
    
    // Show loading overlay if requested
    if (showLoadingOverlay) {
      console.log(`[@component:RecHostStreamModal] Setting isQualitySwitching=true (showLoadingOverlay=${showLoadingOverlay})`);
      setIsQualitySwitching(true); // Show loading overlay
      
      // Only pause existing video on manual quality switch, NOT on initial load
      if (!isInitialLoad) {
        console.log(`[@component:RecHostStreamModal] Setting shouldPausePlayer=true (manual quality switch)`);
        setShouldPausePlayer(true); // Pause existing player to prevent corruption during FFmpeg restart
      } else {
        console.log(`[@component:RecHostStreamModal] Keeping shouldPausePlayer=false (initial load)`);
      }
    }
    
    try {
      const response = await fetch(buildServerUrl('/server/system/restartHostStreamService'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host_name: host.host_name,
          device_id: device?.device_id || 'device1',
          quality: targetQuality
        })
      });
      
      if (response.ok) {
        console.log(`[@component:RecHostStreamModal] Stream restart initiated for ${targetQuality.toUpperCase()} - starting to poll for stabilized stream`);
        // Start polling for new stream if we showed the loading overlay
        if (showLoadingOverlay) {
          pollForNewStream(device?.device_id || 'device1');
        }
      } else {
        if (showLoadingOverlay) {
          showError(`Failed to switch to ${targetQuality.toUpperCase()} quality`);
          setShouldPausePlayer(false);
          setIsQualitySwitching(false);
        }
        console.error(`[@component:RecHostStreamModal] Failed to switch quality: ${response.status}`);
      }
    } catch (error) {
      if (showLoadingOverlay) {
        showError(`Failed to switch to ${targetQuality.toUpperCase()} quality`);
        setShouldPausePlayer(false);
        setIsQualitySwitching(false);
      }
      console.error('[@component:RecHostStreamModal] Quality switch error:', error);
    }
  }, [host.host_name, device?.device_id, showError, pollForNewStream]);

  // Modal lifecycle: LOW quality is always default (no restart needed on mount)
  useEffect(() => {
    console.log('[@component:RecHostStreamModal] Modal opened - reusing existing LOW quality stream (no restart)');

    // Cleanup: ensure LOW quality when component unmounts (for safety)
    return () => {
      const finalQuality = currentQualityRef.current; // Read from ref to get LATEST value
      console.log(`[@component:RecHostStreamModal] Component unmounting, current quality: ${finalQuality}`);
      setIsStreamActive(false);
      
      // Only restart if we're NOT already at LOW quality
      if (finalQuality !== 'low') {
        console.log(`[@component:RecHostStreamModal] Reverting from ${finalQuality.toUpperCase()} to LOW`);
        fetch(buildServerUrl('/server/system/restartHostStreamService'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host_name: host.host_name,
            device_id: device?.device_id || 'device1',
            quality: 'low'
          })
        }).catch(err => console.error('[@component:RecHostStreamModal] Failed to revert to LOW:', err));
      } else {
        console.log('[@component:RecHostStreamModal] Already at LOW quality - no restart needed');
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount/unmount

  // Handle quality selection - for ToggleButtonGroup
  const handleQualityChange = useCallback(async (
    _event: React.MouseEvent<HTMLElement>,
    newQuality: 'low' | 'sd' | 'hd' | null,
  ) => {
    if (!newQuality || newQuality === currentQuality) return; // No change needed or null value
    
    console.log(`[@component:RecHostStreamModal] ===== QUALITY BUTTON CLICKED =====`);
    console.log(`[@component:RecHostStreamModal] Switching from ${currentQuality.toUpperCase()} to ${newQuality.toUpperCase()}`);
    
    // Use common function with loading overlay enabled, NOT initial load (so it blocks HLS)
    await switchQuality(newQuality, true, false); // showLoadingOverlay=true, isInitialLoad=false
  }, [currentQuality, switchQuality]);

  // Handle player ready after quality switch
  const handlePlayerReady = useCallback(() => {
    console.log(`[@component:RecHostStreamModal] ===== PLAYER READY CALLBACK =====`);
    console.log(`[@component:RecHostStreamModal] isQualitySwitching=${isQualitySwitching}`);
    if (isQualitySwitching) {
      console.log('[@component:RecHostStreamModal] Player reloaded successfully - hiding overlay');
      setIsQualitySwitching(false);
    } else {
      console.log('[@component:RecHostStreamModal] Player ready but not during quality switch - ignoring');
    }
  }, [isQualitySwitching]);

  // Handle video time update for archive monitoring
  const handleVideoTimeUpdate = useCallback((time: number) => {
    // In archive mode, we only care about time updates when monitoring is enabled.
    if (isLiveMode || !monitoringMode) return;

    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    // Only update at most every 500ms and when time actually changes by >= 0.5s
    if (now - lastVideoTimeUpdateRef.current < 500) return;
    if (lastVideoTimeValueRef.current >= 0 && Math.abs(time - lastVideoTimeValueRef.current) < 0.5) return;

    lastVideoTimeUpdateRef.current = now;
    lastVideoTimeValueRef.current = time;
    setCurrentVideoTime(time);
  }, [isLiveMode, monitoringMode]);

  // Handle video pause - trigger AI analysis (called ONLY when video pauses)
  const handleVideoPause = useCallback(() => {
    // Only trigger AI analysis in live mode with monitoring ON
    if (isLiveMode && monitoringMode && monitoringData.latestAnalysis) {
      const sequence = monitoringData.analysisTimestamp || '000000';
      const imageUrl = buildCaptureUrl(host, sequence, device?.device_id || 'device1');
      console.log(`[@component:RecHostStreamModal] 🎬 Video paused in live mode - triggering AI analysis for sequence: ${sequence}`);
      monitoringData.requestAIAnalysisForFrame(imageUrl, sequence);
    } else if (!isLiveMode) {
      console.log(`[@component:RecHostStreamModal] 🎬 Video paused in archive mode - AI analysis handled by time change`);
    } else {
      console.log(`[@component:RecHostStreamModal] 🎬 Video paused but monitoring is OFF - skipping AI analysis`);
    }
  }, [isLiveMode, monitoringMode, monitoringData, host, device]);

  // Handle screenshot - call API and open image in new tab
  const handleScreenshot = useCallback(async () => {
    try {
      const response = await fetch(buildServerUrl('/server/av/takeScreenshot'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host_name: host.host_name,
          device_id: device?.device_id || 'device1'
        })
      });
      
      const result = await response.json();
      if (result.success && result.screenshot_url) {
        window.open(result.screenshot_url, '_blank');
        console.log(`[@component:RecHostStreamModal] Opening screenshot: ${result.screenshot_url}`);
      } else {
        showError(`Screenshot failed: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      showError('Failed to take screenshot');
      console.error('[@component:RecHostStreamModal] Screenshot error:', error);
    }
  }, [host.host_name, device?.device_id, showError]);

  // Check if device is mobile model (consistent with RecHostPreview)
  const isMobileModel = useMemo(() => {
    const model = device?.device_model;
    if (!model) return false;
    const modelLower = model.toLowerCase();
    return modelLower.includes('mobile');
  }, [device?.device_model]);

  // Stable onReleaseControl callback to prevent re-renders
  const handleReleaseControl = useCallback(() => {
    setShowRemote(false);
    setShowWeb(false);
    // Control release handled by useDeviceControl
  }, []);

  // Handle modal close
  const handleClose = useCallback(async () => {
    console.log('[@component:RecHostStreamModal] Closing modal');

    // Stop any polling
    if (pollingIntervalRef.current) {
      if (typeof pollingIntervalRef.current === 'function') {
        // New hook-based cleanup function
        pollingIntervalRef.current();
      } else {
        // Legacy interval cleanup (fallback)
        clearInterval(pollingIntervalRef.current);
      }
      pollingIntervalRef.current = null;
    }

    // Stop stream before closing
    setIsStreamActive(false);

    // Reset state (useDeviceControl handles cleanup automatically)
    setShowRemote(false);
    setShowWeb(false);
    setMonitoringMode(false);
    setAiAgentMode(false);
    setRestartMode(false);
    // Quality revert handled by useEffect cleanup (reads from ref for accurate state)
    setShouldPausePlayer(false);
    setIsQualitySwitching(false);
    onClose();
  }, [onClose]);

  // Prevent body scrolling when modal is open
  useEffect(() => {
    // Store original overflow value
    const originalOverflow = document.body.style.overflow;
    const originalPaddingRight = document.body.style.paddingRight;
    
    // Calculate scrollbar width to prevent layout shift
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    
    // Hide body scrollbar and compensate for layout shift
    document.body.style.overflow = 'hidden';
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }
    
    console.log('[@component:RecHostStreamModal] Body scroll disabled, scrollbarWidth:', scrollbarWidth);

    return () => {
      // Restore original overflow and padding
      document.body.style.overflow = originalOverflow;
      document.body.style.paddingRight = originalPaddingRight;
      console.log('[@component:RecHostStreamModal] Body scroll restored');
    };
  }, []);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [handleClose]);

  // Show control errors
  useEffect(() => {
    if (controlError) {
      showError(controlError);
      clearError();
    }
  }, [controlError, showError, clearError]);

  // Show URL error if stream fetch failed
  useEffect(() => {
    if (urlError) {
      showError(`Stream URL error: ${urlError}`);
    }
  }, [urlError, showError]);

  // AI errors are handled by useAI hook - no duplicate toasts needed here

  return (
      <Box
        sx={{
          position: 'fixed',
          inset: 0,
          zIndex: getZIndex('MODAL_CONTENT'),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
        }}
      >
      <Box
        sx={{
          width: '95vw',
          height: '90vh',
          backgroundColor: 'background.paper',
          borderRadius: 2,
          boxShadow: 24,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <RecStreamModalHeader
          host={host}
          device={device}
          monitoringMode={monitoringMode}
          restartMode={restartMode}
          isLiveMode={isLiveMode}
          currentQuality={currentQuality}
          isQualitySwitching={isQualitySwitching}
          isMuted={isMuted}
          isControlActive={isControlActive}
          isControlLoading={isControlLoading}
          aiAgentMode={aiAgentMode}
          showWeb={showWeb}
          showRemote={showRemote}
          isDesktopDevice={isDesktopDevice}
          hasPowerControl={!!hasPowerControl}
          onScreenshot={handleScreenshot}
          onToggleLiveMode={handleToggleLiveMode}
          onQualityChange={handleQualityChange}
          onToggleMute={() => setIsMuted((prev) => !prev)}
          onToggleControl={handleToggleControl}
          onToggleMonitoring={handleToggleMonitoring}
          onToggleRestart={handleToggleRestart}
          onToggleAiAgent={handleToggleAiAgent}
          onToggleWeb={handleToggleWeb}
          onToggleRemote={handleToggleRemote}
          onClose={handleClose}
        />

        {/* Main Content */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            overflow: 'hidden',
            backgroundColor: 'black',
            position: 'relative',
          }}
        >
          <RecStreamContainer
            host={host}
            device={device}
            streamUrl={streamUrl || undefined}
            isLoadingUrl={isLoadingUrl}
            urlError={urlError}
            monitoringMode={monitoringMode}
            restartMode={restartMode}
            isLiveMode={isLiveMode}
            isControlActive={isControlActive}
            currentQuality={currentQuality}
            isQualitySwitching={isQualitySwitching}
            shouldPausePlayer={shouldPausePlayer}
            isMuted={isMuted}
            isMobileModel={isMobileModel}
            showRemote={showRemote}
            showWeb={showWeb}
            finalStreamContainerDimensions={finalStreamContainerDimensions}
            calculateVncScaling={calculateVncScaling}
            onPlayerReady={handlePlayerReady}
            onVideoTimeUpdate={handleVideoTimeUpdate}
            onVideoPause={handleVideoPause}
            sharedVideoRef={sharedVideoRef}
            monitoringAnalysis={monitoringData.latestAnalysis || undefined}
            subtitleAnalysis={monitoringData.latestSubtitleAnalysis || undefined}
            languageMenuAnalysis={monitoringData.latestLanguageMenuAnalysis || undefined}
            aiDescription={monitoringData.latestAIDescription || undefined}
            errorTrendData={monitoringData.errorTrendData || undefined}
            analysisTimestamp={monitoringData.analysisTimestamp || undefined}
            isAIAnalyzing={monitoringData.isAIAnalyzing}
          />

          {/* Panel Manager */}
          <RecPanelManager
                  host={host}
            device={device}
            showRemote={showRemote}
            showWeb={showWeb}
            isControlActive={isControlActive}
            isDesktopDevice={isDesktopDevice}
            finalStreamContainerDimensions={finalStreamContainerDimensions}
                  onReleaseControl={handleReleaseControl}
          />

          {/* AI Agent Panel */}
          <AIExecutionPanel
            host={host}
            device={device!}
            isControlActive={isControlActive}
            isVisible={aiAgentMode && isControlActive}
            onDisambiguationDataChange={handleDisambiguationDataChange}
          />
        </Box>
      </Box>

      {/* AI Disambiguation Modal - Rendered at top level with proper z-index */}
      {disambiguationData && disambiguationResolve && disambiguationCancel && (
        <PromptDisambiguation
          ambiguities={disambiguationData.ambiguities}
          autoCorrections={disambiguationData.auto_corrections}
          availableNodes={disambiguationData.available_nodes}
          onResolve={(selections, saveToDb) => {
            disambiguationResolve(selections, saveToDb);
            setDisambiguationData(null);
          }}
          onCancel={() => {
            disambiguationCancel();
            setDisambiguationData(null);
          }}
          onEditPrompt={() => {
            // Close modal and cancel AI execution so user can edit their prompt
            disambiguationCancel();
            setDisambiguationData(null);
            // User can now edit the prompt in AIExecutionPanel
          }}
        />
      )}
    </Box>
  );
};
