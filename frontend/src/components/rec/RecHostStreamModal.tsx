import { Box } from '@mui/material';
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';

import { VNCStateProvider } from '../../contexts/VNCStateContext';
import { useStream } from '../../hooks/controller';
import { useDeviceControlWithForceUnlock } from '../../hooks/useDeviceControlWithForceUnlock';
import { useToast } from '../../hooks/useToast';
import { useMonitoring } from '../../hooks/monitoring/useMonitoring';
import { Host, Device } from '../../types/common/Host_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { buildServerUrl, pollForFreshStream, getCaptureUrlFromStream } from '../../utils/buildUrlUtils';
import { DEFAULT_DEVICE_RESOLUTION } from '../../config/deviceResolutions';
import { calculateVncScaling } from '../../utils/vncUtils';
import { AIExecutionPanel } from '../ai';
import { PromptDisambiguation } from '../ai/PromptDisambiguation';
import { AIImageQueryModal } from '../monitoring';
import { ConfirmDialog } from '../common/ConfirmDialog';

import { RecStreamModalHeader } from './RecStreamModalHeader';
import { RecStreamContainer } from './RecStreamContainer';
import { RecPanelManager } from './RecPanelManager';
import { ScriptRunningOverlay } from './ScriptRunningOverlay';

interface RecHostStreamModalProps {
  host: Host;
  device?: Device; // Optional device for device-specific operations
  isOpen: boolean;
  onClose: () => void;
  showRemoteByDefault?: boolean;
}

export const RecHostStreamModal: React.FC<RecHostStreamModalProps> = ({
  host,
  device,
  isOpen,
  onClose,
  showRemoteByDefault = false,
}) => {
  // Early return if not open - prevents hooks from running
  if (!isOpen || !host) return null;

  return (
    <VNCStateProvider>
      <RecHostStreamModalContent
        host={host}
        device={device}
        onClose={onClose}
        showRemoteByDefault={showRemoteByDefault}
      />
    </VNCStateProvider>
  );
};

// Separate component that only mounts when modal is open
const RecHostStreamModalContent: React.FC<{
  host: Host;
  device?: Device;
  onClose: () => void;
  showRemoteByDefault: boolean;
}> = ({ host, device, onClose, showRemoteByDefault }) => {
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
  const isQualitySwitchingRef = useRef<boolean>(false); // Ref to track quality switching for callback race conditions
  const [shouldPausePlayer, setShouldPausePlayer] = useState<boolean>(false); // Pause player during transition
  const [currentVideoTime, setCurrentVideoTime] = useState<number>(0); // Track video currentTime for archive monitoring
  const pollingIntervalRef = useRef<NodeJS.Timeout | (() => void) | null>(null);
  const qualitySwitchRetryCountRef = useRef<number>(0); // Track retry attempts for quality switch
  // Throttle frequent video time updates to avoid excessive re-renders
  const lastVideoTimeUpdateRef = useRef<number>(0);
  const lastVideoTimeValueRef = useRef<number>(-1);
  
  // Helper function to update isQualitySwitching state and ref together
  const setIsQualitySwitchingState = useCallback((value: boolean) => {
    isQualitySwitchingRef.current = value;
    setIsQualitySwitching(value);
  }, []);

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
    console.log('[@RecHostStreamModal] handleDisambiguationDataChange called');
    console.log('[@RecHostStreamModal] Disambiguation data:', data);
    console.log('[@RecHostStreamModal] Has ambiguities:', !!data?.ambiguities);
    
    setDisambiguationData(data);
    setDisambiguationResolve(() => resolve);
    setDisambiguationCancel(() => cancel);
    
    console.log('[@RecHostStreamModal] Disambiguation state updated, modal should appear');
  }, []);

  // AI Image Query state
  const [isImageQueryVisible, setIsImageQueryVisible] = useState(false);
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null);
  const [currentSegmentUrl, setCurrentSegmentUrl] = useState<string | null>(null);

  // Hooks - now only run when modal is actually open
  const { showError, showWarning } = useToast();

  // Use enhanced device control hook with force unlock capability
  const {
    isControlActive,
    isControlLoading,
    controlError,
    handleDeviceControl,
    clearError,
    confirmDialogState,
    confirmDialogHandleConfirm,
    confirmDialogHandleCancel,
  } = useDeviceControlWithForceUnlock({
    host,
    device_id: device?.device_id || 'device1',
    sessionId: 'rec-stream-modal-session',
    autoCleanup: true, // Auto-release on unmount
    requireTreeId: false, // REC modal doesn't require tree_id (not navigation-based)
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

  // Check if this is a desktop device (host_vnc) - needed for dimension calculation
  const isDesktopDevice = useMemo(() => {
    return device?.device_model === 'host_vnc';
  }, [device?.device_model]);

  // Check if device is mobile model (consistent with RecHostPreview)
  const isMobileModel = useMemo(() => {
    const model = device?.device_model;
    if (!model) return false;
    const modelLower = model.toLowerCase();
    return modelLower.includes('mobile');
  }, [device?.device_model]);

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

    // Simple 80/20 rule: If any panel showing, stream gets 80%, otherwise 100%
    const hasAnyPanel = showRemote || (showWeb && isDesktopDevice);
    const streamAreaWidth = hasAnyPanel ? modalWidth * 0.80 : modalWidth;

    // Max height available for the stream inside the modal (respect header)
    const maxStreamAreaHeight = modalHeight - actualHeaderHeight;

    // Ideal height to keep the HDMI/HLS stream at the target aspect ratio (16:9)
    const targetAspectRatio = DEFAULT_DEVICE_RESOLUTION.height / DEFAULT_DEVICE_RESOLUTION.width;
    const idealStreamHeightFromAspect = streamAreaWidth * targetAspectRatio;

    // Final height: as tall as possible while fitting inside the modal, preserving aspect ratio
    const streamAreaHeight = Math.min(maxStreamAreaHeight, idealStreamHeightFromAspect);

    // Modal position (centered)
    const modalX = (windowWidth - modalWidth) / 2;
    const modalY = (windowHeight - modalHeight) / 2;

    // Stream container position calculation
    const streamX = modalX;
    
    // Calculate stream Y position - this should be the actual content area position
    // The content area starts immediately after the header (including padding)
    // Adjusted offset to align overlay with actual video content area
    const additionalOffset = -8; // Corrected offset after testing (was 32, reduced by 40)
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
  }, [isDesktopDevice, showRemote, showWeb]);

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
      
      // When switching to Last 24h mode (newMode = false), automatically disable control-dependent features AND monitoring
      if (!newMode) {
        console.log(`[@component:RecHostStreamModal] Switching to Last 24h - disabling remote, AI agent, restart, and monitoring`);
        setShowRemote(false);
        setAiAgentMode(false);
        setRestartMode(false);
        setMonitoringMode(false); // Disable monitoring in archive mode
      }
      
      return newMode;
    });
  }, []);

  // Poll for new stream availability using hook function
  const pollForNewStream = useCallback((deviceId: string, targetQuality: 'low' | 'sd' | 'hd') => {
    console.log(`[@component:RecHostStreamModal] Starting polling for new stream using hook function (retry count: ${qualitySwitchRetryCountRef.current})`);
    
    const cleanup = pollForFreshStream(
      host,
      deviceId,
      // onReady callback
      () => {
        console.log(`[@component:RecHostStreamModal] ✅ Fresh stream ready from hook - allowing player to reinitialize`);
        qualitySwitchRetryCountRef.current = 0; // Reset retry count on success
        setShouldPausePlayer(false);
        // Don't set isQualitySwitching=false here - let handlePlayerReady do it when player actually loads
        console.log(`[@component:RecHostStreamModal] Waiting for player to report ready via onPlayerReady callback...`);
        // Clear the polling reference
        pollingIntervalRef.current = null;
      },
      // onTimeout callback
      (error: string) => {
        console.warn(`[@component:RecHostStreamModal] Polling timeout from hook - ${error} (retry count: ${qualitySwitchRetryCountRef.current})`);
        
        // Retry once if this is the first failure
        if (qualitySwitchRetryCountRef.current === 0) {
          qualitySwitchRetryCountRef.current = 1;
          console.log(`[@component:RecHostStreamModal] 🔄 First timeout - retrying quality switch to ${targetQuality.toUpperCase()} (attempt 2/2)`);
          pollingIntervalRef.current = null;
          
          // Retry the quality switch after a brief delay
          setTimeout(async () => {
            try {
              const response = await fetch(buildServerUrl('/server/system/restartHostStreamService'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  host_name: host.host_name,
                  device_id: deviceId,
                  quality: targetQuality
                })
              });
              
              if (response.ok) {
                console.log(`[@component:RecHostStreamModal] Retry stream restart initiated for ${targetQuality.toUpperCase()}`);
                pollForNewStream(deviceId, targetQuality); // Start polling again
              } else {
                console.error(`[@component:RecHostStreamModal] Retry failed: ${response.status}`);
                qualitySwitchRetryCountRef.current = 0;
                setShouldPausePlayer(false);
                setIsQualitySwitchingState(false);
                showError(`Failed to switch to ${targetQuality.toUpperCase()} quality after retry`);
              }
            } catch (retryError) {
              console.error('[@component:RecHostStreamModal] Retry error:', retryError);
              qualitySwitchRetryCountRef.current = 0;
              setShouldPausePlayer(false);
              setIsQualitySwitchingState(false);
              showError(`Failed to switch to ${targetQuality.toUpperCase()} quality after retry`);
            }
          }, 1000); // 1 second delay before retry
        } else {
          // Already retried once, give up
          console.error(`[@component:RecHostStreamModal] ❌ Quality switch failed after retry - giving up`);
          qualitySwitchRetryCountRef.current = 0;
          setShouldPausePlayer(false);
          setIsQualitySwitchingState(false);
          showError(`Stream failed to reload after switching to ${targetQuality.toUpperCase()} quality. Please try again.`);
          pollingIntervalRef.current = null;
        }
      }
    );
    
    // Store cleanup function reference for manual cleanup if needed
    pollingIntervalRef.current = cleanup as any; // Store cleanup function instead of interval
  }, [host, pollForFreshStream, showWarning, showError]);

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
      setIsQualitySwitchingState(true); // Show loading overlay
      
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
          pollForNewStream(device?.device_id || 'device1', targetQuality);
        }
      } else {
        if (showLoadingOverlay) {
          showError(`Failed to switch to ${targetQuality.toUpperCase()} quality`);
          setShouldPausePlayer(false);
          setIsQualitySwitchingState(false);
        }
        console.error(`[@component:RecHostStreamModal] Failed to switch quality: ${response.status}`);
      }
    } catch (error) {
      if (showLoadingOverlay) {
        showError(`Failed to switch to ${targetQuality.toUpperCase()} quality`);
        setShouldPausePlayer(false);
        setIsQualitySwitchingState(false);
      }
      console.error('[@component:RecHostStreamModal] Quality switch error:', error);
    }
  }, [host.host_name, device?.device_id, showError, pollForNewStream, setIsQualitySwitchingState]);

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
    console.log(`[@component:RecHostStreamModal] isQualitySwitching=${isQualitySwitchingRef.current}, shouldPausePlayer=${shouldPausePlayer}`);
    if (isQualitySwitchingRef.current) {
      console.log('[@component:RecHostStreamModal] Player reloaded successfully after quality switch - hiding overlay and resuming playback');
      setIsQualitySwitchingState(false);
    } else {
      console.log('[@component:RecHostStreamModal] Player ready but not during quality switch - ignoring (normal initial load or other event)');
    }
  }, [shouldPausePlayer, setIsQualitySwitchingState]);

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


  // Handle screenshot - calculate from current segment and open in new tab (live mode only)
  const handleScreenshot = useCallback(async () => {
    console.log('[@component:RecHostStreamModal] 📸 Screenshot button clicked!', {
      isLiveMode,
      restartMode,
      currentSegmentUrl,
      hasDevice: !!device,
      hasHost: !!host,
      deviceModel: device?.device_model
    });
    
    if (!isLiveMode || restartMode) {
      console.warn('[@component:RecHostStreamModal] ❌ Not in live mode');
      showError('Screenshot is only available in Live mode');
      return;
    }
    
    // VNC/Desktop devices: Use direct screenshot API (no HLS segments)
    const isVncDevice = device?.device_model === 'host_vnc';
    if (isVncDevice) {
      console.log('[@component:RecHostStreamModal] 🖥️ VNC device detected - using direct screenshot API');
      
      try {
        const response = await fetch(buildServerUrl('/server/av/takeScreenshot'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host_name: host.host_name,
            device_id: device.device_id
          })
        });
        
        if (!response.ok) {
          console.error('[@component:RecHostStreamModal] ❌ Screenshot API failed:', response.status);
          showError('Failed to take screenshot');
          return;
        }
        
        const result = await response.json();
        if (result.success && result.screenshot_url) {
          console.log(`[@component:RecHostStreamModal] ✅ Opening screenshot: ${result.screenshot_url}`);
          window.open(result.screenshot_url, '_blank');
        } else {
          console.error('[@component:RecHostStreamModal] ❌ Screenshot API returned error:', result.error);
          showError('Failed to take screenshot');
        }
      } catch (error) {
        console.error('[@component:RecHostStreamModal] ❌ Screenshot request failed:', error);
        showError('Failed to take screenshot');
      }
      return;
    }
    
    // HLS devices: Use segment-based screenshot
    if (!currentSegmentUrl) {
      console.warn('[@component:RecHostStreamModal] ❌ No currentSegmentUrl - video not playing or segment not tracked');
      showError('Failed to take screenshot (video segment missing)');
      return;
    }

    console.log('[@component:RecHostStreamModal] ✅ Calling getCaptureUrlFromStream with:', currentSegmentUrl);
    const captureUrl = await getCaptureUrlFromStream(currentSegmentUrl, device, host);
    if (captureUrl) {
      console.log(`[@component:RecHostStreamModal] ✅ Opening screenshot: ${captureUrl}`);
      window.open(captureUrl, '_blank');
    } else {
      console.error('[@component:RecHostStreamModal] ❌ getCaptureUrlFromStream returned null');
      showError('Could not determine current frame');
    }
  }, [currentSegmentUrl, device, host, getCaptureUrlFromStream, showError, isLiveMode, restartMode]);

  // Handle AI Image Query - calculate capture URL from current segment (live mode only, not restart)
  const handleAIImageQuery = useCallback(async () => {
    console.log('[@component:RecHostStreamModal] 🤖 AI Image Query clicked!', {
      isLiveMode,
      restartMode,
      currentSegmentUrl,
      deviceModel: device?.device_model
    });
    
    if (!isLiveMode || restartMode) {
      console.warn('[@component:RecHostStreamModal] ❌ Not in live mode or in restart mode');
      return;
    }
    
    // VNC/Desktop devices: Use direct screenshot API (no HLS segments)
    const isVncDevice = device?.device_model === 'host_vnc';
    if (isVncDevice) {
      console.log('[@component:RecHostStreamModal] 🖥️ VNC device detected - using direct screenshot API for AI query');
      
      try {
        const response = await fetch(buildServerUrl('/server/av/takeScreenshot'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host_name: host.host_name,
            device_id: device.device_id
          })
        });
        
        if (!response.ok) {
          console.error('[@component:RecHostStreamModal] ❌ Screenshot API failed for AI query:', response.status);
          showError('Failed to capture image for AI query');
          return;
        }
        
        const result = await response.json();
        if (result.success && result.screenshot_url) {
          console.log(`[@component:RecHostStreamModal] ✅ AI Image Query capture URL: ${result.screenshot_url}`);
          setCapturedImageUrl(result.screenshot_url);
          setIsImageQueryVisible(true);
        } else {
          console.error('[@component:RecHostStreamModal] ❌ Screenshot API returned error for AI query:', result.error);
          showError('Failed to capture image for AI query');
        }
      } catch (error) {
        console.error('[@component:RecHostStreamModal] ❌ Screenshot request failed for AI query:', error);
        showError('Failed to capture image for AI query');
      }
      return;
    }
    
    // HLS devices: Use segment-based screenshot
    if (!currentSegmentUrl) {
      console.warn('[@component:RecHostStreamModal] ❌ No currentSegmentUrl for AI query');
      return;
    }
    
    const captureUrl = await getCaptureUrlFromStream(currentSegmentUrl, device, host);
    if (captureUrl) {
      console.log(`[@RecHostStreamModal] AI Image Query capture URL: ${captureUrl}`);
      setCapturedImageUrl(captureUrl);
      setIsImageQueryVisible(true);
    } else {
      showError('Could not determine current frame');
    }
  }, [currentSegmentUrl, device, host, getCaptureUrlFromStream, showError, isLiveMode, restartMode, setCapturedImageUrl, setIsImageQueryVisible]);

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
    setIsQualitySwitchingState(false);
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
          onAIImageQuery={handleAIImageQuery}
          onToggleLiveMode={handleToggleLiveMode}
          onQualityChange={handleQualityChange}
          onToggleMute={() => setIsMuted((prev) => !prev)}
          onToggleControl={handleDeviceControl}
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
          {/* Stream Container */}
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
            onCurrentSegmentChange={setCurrentSegmentUrl}
            // Monitoring data props
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

          {/* Script Running Overlay - Show when script is running */}
          {device?.has_running_deployment && (
            <ScriptRunningOverlay
              host={host}
              device_id={device.device_id}
            />
          )}
        </Box>
      </Box>

      {/* AI Disambiguation Modal - Rendered at top level with proper z-index */}
      {disambiguationData && disambiguationResolve && disambiguationCancel && (
        <>
          {console.log('[@RecHostStreamModal] Rendering PromptDisambiguation modal')}
          {console.log('[@RecHostStreamModal] Modal data:', {
            hasAmbiguities: !!disambiguationData.ambiguities,
            ambiguitiesLength: disambiguationData.ambiguities?.length,
            hasAutoCorrections: !!disambiguationData.auto_corrections,
            hasAvailableNodes: !!disambiguationData.available_nodes
          })}
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
        </>
      )}

      {/* AI Image Query Modal */}
      <AIImageQueryModal
        isVisible={isImageQueryVisible}
        imageUrl={capturedImageUrl}
        host={host}
        device={device!}
        onClose={() => setIsImageQueryVisible(false)}
      />

      {/* Force Unlock Confirmation Dialog */}
      <ConfirmDialog
        open={confirmDialogState.open}
        title={confirmDialogState.title}
        message={confirmDialogState.message}
        confirmText={confirmDialogState.confirmText}
        cancelText={confirmDialogState.cancelText}
        confirmColor={confirmDialogState.confirmColor}
        onConfirm={confirmDialogHandleConfirm}
        onCancel={confirmDialogHandleCancel}
      />
    </Box>
  );
};
