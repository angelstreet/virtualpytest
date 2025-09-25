import {
  Close as CloseIcon,
  Tv as TvIcon,
  Analytics as AnalyticsIcon,
  SmartToy as AIIcon,
  Language as WebIcon,
  VolumeOff as VolumeOffIcon,
  VolumeUp as VolumeUpIcon,
  Refresh as RefreshIcon,
  RadioButtonChecked as LiveIcon,
  History as ArchiveIcon,
} from '@mui/icons-material';
import { Box, IconButton, Typography, Button, CircularProgress } from '@mui/material';
import React, { useState, useCallback, useEffect, useMemo } from 'react';

import { DEFAULT_DEVICE_RESOLUTION } from '../../config/deviceResolutions';
import { useModal } from '../../contexts/ModalContext';
import { VNCStateProvider } from '../../contexts/VNCStateContext';
import { useStream } from '../../hooks/controller';
import { useRec } from '../../hooks/pages/useRec';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import { useToast } from '../../hooks/useToast';
import { Host, Device } from '../../types/common/Host_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { AIExecutionPanel } from '../ai';
import { EnhancedHLSPlayer } from '../video/EnhancedHLSPlayer';
import { DesktopPanel } from '../controller/desktop/DesktopPanel';
import { PowerButton } from '../controller/power/PowerButton';
import { RemotePanel } from '../controller/remote/RemotePanel';
import { WebPanel } from '../controller/web/WebPanel';
import { MonitoringPlayer } from '../monitoring/MonitoringPlayer';

import { RestartPlayer } from './RestartPlayer';

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
  // Global modal state
  const { setAnyModalOpen } = useModal();

  // Local state
  const [showRemote, setShowRemote] = useState<boolean>(showRemoteByDefault);
  const [showWeb, setShowWeb] = useState<boolean>(false);
  const [monitoringMode, setMonitoringMode] = useState<boolean>(false);
  const [aiAgentMode, setAiAgentMode] = useState<boolean>(false);
  const [restartMode, setRestartMode] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(true); // Start muted by default
  const [, setIsStreamActive] = useState<boolean>(true); // Stream lifecycle management
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true); // Start in live mode

  // Set global modal state when component mounts/unmounts
  useEffect(() => {
    setAnyModalOpen(true);
    return () => {
      setAnyModalOpen(false);
    };
  }, [setAnyModalOpen]);

  // Cleanup stream when component unmounts
  useEffect(() => {
    return () => {
      console.log('[@component:RecHostStreamModal] Component unmounting, stopping stream');
      setIsStreamActive(false);
    };
  }, []);

  // Hooks - now only run when modal is actually open
  const { showError, showWarning } = useToast();

  // Get baseUrlPatterns and VNC scaling for monitoring
  const { baseUrlPatterns, calculateVncScaling } = useRec();

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

  // Handle monitoring mode toggle
  const handleToggleMonitoring = useCallback(() => {
    if (!isControlActive) {
      showWarning('Please take control of the device first to enable monitoring');
      return;
    }

    setMonitoringMode((prev) => {
      const newMode = !prev;
      console.log(`[@component:RecHostStreamModal] Monitoring mode toggled: ${newMode}`);

      // Disable AI agent mode and restart mode when enabling monitoring
      if (newMode) {
        setAiAgentMode(false);
        setRestartMode(false);
        // Remove auto-show remote - user must click remote individually
      }

      return newMode;
    });
  }, [isControlActive, showWarning]);

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
      console.log(`[@component:RecHostStreamModal] Live mode toggled: ${newMode ? 'Live' : '24h Archive'}`);
      return newMode;
    });
  }, []);

  // Stable device resolution to prevent re-renders
  const stableDeviceResolution = useMemo(() => DEFAULT_DEVICE_RESOLUTION, []);

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

    // Stop stream before closing
    setIsStreamActive(false);

    // Reset state (useDeviceControl handles cleanup automatically)
    setShowRemote(false);
    setShowWeb(false);
    setMonitoringMode(false);
    setAiAgentMode(false);
    setRestartMode(false);
    onClose();
  }, [onClose]);

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
          alignItems: 'flex-end',
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
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: 'grey.800',
            color: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderRadius: '8px 8px 0 0',
            minHeight: 48,
          }}
        >
          <Typography variant="h6" component="h2">
            {device?.device_name || host.host_name} -{' '}
            {monitoringMode ? 'Monitoring' : restartMode ? 'Restart Player' : isLiveMode ? 'Live Stream' : '24h Archive'}
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Live/24h Mode Toggle Button - Only show when NOT in monitoring or restart mode */}
            {!monitoringMode && !restartMode && (
              <Button
                variant={isLiveMode ? 'contained' : 'outlined'}
                size="small"
                onClick={handleToggleLiveMode}
                startIcon={isLiveMode ? <LiveIcon /> : <ArchiveIcon />}
                color={isLiveMode ? 'error' : 'primary'}
                sx={{
                  fontSize: '0.75rem',
                  minWidth: 100,
                  color: isLiveMode ? 'white' : 'inherit',
                }}
                title={isLiveMode ? 'Switch to 24h Archive' : 'Switch to Live Stream'}
              >
                {isLiveMode ? 'Live' : '24h'}
              </Button>
            )}

            {/* Volume Toggle Button - Only show when NOT in monitoring mode */}
            {!monitoringMode && !restartMode && (
              <IconButton
                onClick={() => setIsMuted((prev) => !prev)}
                sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
                aria-label={isMuted ? 'Unmute' : 'Mute'}
                title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
              >
                {isMuted ? <VolumeOffIcon /> : <VolumeUpIcon />}
              </IconButton>
            )}

            {/* Take Control Button */}
            <Button
              variant={isControlActive ? 'contained' : 'outlined'}
              size="small"
              onClick={handleToggleControl}
              disabled={isControlLoading}
              startIcon={isControlLoading ? <CircularProgress size={16} /> : <TvIcon />}
              color={isControlActive ? 'success' : 'primary'}
              sx={{
                fontSize: '0.75rem',
                minWidth: 120,
                color: isControlActive ? 'white' : 'inherit',
              }}
              title={
                isControlLoading
                  ? 'Processing...'
                  : isControlActive
                    ? 'Release Control'
                    : 'Take Control'
              }
            >
              {isControlLoading
                ? 'Processing...'
                : isControlActive
                  ? 'Release Control'
                  : 'Take Control'}
            </Button>

            {/* Power Control Button */}
            {hasPowerControl && device && (
              <PowerButton host={host} device={device} disabled={!isControlActive} />
            )}

            {/* Monitoring Toggle Button */}
            <Button
              variant={monitoringMode ? 'contained' : 'outlined'}
              size="small"
              onClick={handleToggleMonitoring}
              disabled={!isControlActive}
              startIcon={<AnalyticsIcon />}
              color={monitoringMode ? 'warning' : 'primary'}
              sx={{
                fontSize: '0.75rem',
                minWidth: 120,
                color: monitoringMode ? 'white' : 'inherit',
              }}
              title={
                !isControlActive
                  ? 'Take control first to enable monitoring'
                  : monitoringMode
                    ? 'Disable Monitoring'
                    : 'Enable Monitoring'
              }
            >
              {monitoringMode ? 'Stop Monitoring' : 'Monitoring'}
            </Button>

            {/* Restart Toggle Button */}
            <Button
              variant={restartMode ? 'contained' : 'outlined'}
              size="small"
              onClick={handleToggleRestart}
              disabled={!isControlActive}
              startIcon={<RefreshIcon />}
              color={restartMode ? 'secondary' : 'primary'}
              sx={{
                fontSize: '0.75rem',
                minWidth: 120,
                color: restartMode ? 'white' : 'inherit',
              }}
              title={
                !isControlActive
                  ? 'Take control first to enable restart mode'
                  : restartMode
                    ? 'Disable Restart Player'
                    : 'Enable Restart Player'
              }
            >
              {restartMode ? 'Stop Restart' : 'Restart'}
            </Button>

            {/* AI Agent Toggle Button */}
            <Button
              variant={aiAgentMode ? 'contained' : 'outlined'}
              size="small"
              onClick={handleToggleAiAgent}
              disabled={!isControlActive}
              startIcon={<AIIcon />}
              color={aiAgentMode ? 'info' : 'primary'}
              sx={{
                fontSize: '0.75rem',
                minWidth: 120,
                color: aiAgentMode ? 'white' : 'inherit',
              }}
              title={
                !isControlActive
                  ? 'Take control first to enable AI agent'
                  : aiAgentMode
                    ? 'Disable AI Agent'
                    : 'Enable AI Agent'
              }
            >
              {aiAgentMode ? 'Stop AI Agent' : 'AI Agent'}
            </Button>

            {/* Web Panel Toggle Button */}
            {isDesktopDevice && (
              <Button
                variant={showWeb ? 'contained' : 'outlined'}
                size="small"
                onClick={handleToggleWeb}
                disabled={!isControlActive}
                startIcon={<WebIcon />}
                color={showWeb ? 'secondary' : 'primary'}
                sx={{
                  fontSize: '0.75rem',
                  minWidth: 100,
                  color: showWeb ? 'white' : 'inherit',
                }}
                title={
                  !isControlActive
                    ? 'Take control first to use web automation'
                    : showWeb
                      ? 'Hide Web'
                      : 'Show Web '
                }
              >
                {showWeb ? 'Hide Web' : 'Show Web'}
              </Button>
            )}

            {/* Remote/Terminal Toggle Button */}
            <Button
              variant="outlined"
              size="small"
              onClick={handleToggleRemote}
              disabled={!isControlActive}
              sx={{
                fontSize: '0.75rem',
                minWidth: 100,
                color: 'inherit',
              }}
              title={
                !isControlActive
                  ? `Take control first to use ${isDesktopDevice ? 'terminal' : 'remote'}`
                  : showRemote
                    ? `Hide ${isDesktopDevice ? 'Terminal' : 'Remote'}`
                    : `Show ${isDesktopDevice ? 'Terminal' : 'Remote'}`
              }
            >
              {showRemote
                ? `Hide ${isDesktopDevice ? 'Terminal' : 'Remote'}`
                : `Show ${isDesktopDevice ? 'Terminal' : 'Remote'}`}
            </Button>

            {/* Close Button */}
            <IconButton
              onClick={handleClose}
              sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
              aria-label="Close"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

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
          {/* Stream Viewer / Monitoring Player */}
          <Box
            sx={{
              width: (() => {
                if (!isControlActive) return '100%';
                const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
                if (panelCount === 0) return '100%';
                if (panelCount === 1) return '80%'; // Changed from 75% to 80% (100% - 20%)
                return '60%'; // Changed from 50% to 60% (100% - 40% for two 20% panels)
              })(),
              height: '100%', // Use full available height (already excluding header)
              position: 'relative',
              overflow: 'hidden',
              display: 'flex',
              alignItems: isMobileModel ? 'flex-start' : 'center', // Top-align mobile to avoid bottom black bars
              justifyContent: 'center',
              backgroundColor: 'black',
            }}
          >
            {monitoringMode && isControlActive ? (
              <MonitoringPlayer
                host={host}
                device={device!}
                baseUrlPattern={baseUrlPatterns.get(`${host.host_name}-${device?.device_id}`)}
              />
            ) : restartMode && isControlActive ? (
              <RestartPlayer host={host} device={device!} includeAudioAnalysis={true} />
            ) : streamUrl ? (
              // Check if this is a VNC device - use iframe instead of HLS player
              device?.device_model === 'host_vnc' ? (
                (() => {
                  const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
                  const hasPanel = panelCount > 0 && isControlActive;
                  
                  // Calculate target size based on current modal stream area
                  const targetWidth = hasPanel 
                    ? finalStreamContainerDimensions.width * 0.80  // 80% when panels shown (changed from 75%)
                    : finalStreamContainerDimensions.width;        // 100% when no panels
                  const targetHeight = finalStreamContainerDimensions.height;
                  
                  const vncScaling = calculateVncScaling({ 
                    width: targetWidth, 
                    height: targetHeight 
                  });

                  return (
                    <Box
                      sx={{
                        position: 'relative',
                        width: '100%',
                        height: '100%',
                        backgroundColor: 'black',
                        overflow: 'hidden',
                      }}
                    >
                      <iframe
                        src={streamUrl}
                        style={{
                          border: 'none',
                          backgroundColor: '#000',
                          display: 'block',
                          margin: '0 auto', // Center horizontally
                          ...vncScaling, // Apply calculated scaling
                        }}
                        title="VNC Desktop Stream"
                        allow="fullscreen"
                      />
                    </Box>
                  );
                })()
              ) : (
                <EnhancedHLSPlayer
                    deviceId={device?.device_id || 'device1'}
                    hostName={host.host_name}
                    host={host}
                    streamUrl={streamUrl}
                    width="100%"
                    height={isMobileModel ? 600 : 400}
                    autoPlay={!isMuted}
                    isLiveMode={isLiveMode}
                />
              )
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'white',
                }}
              >
                <Typography>
                  {isLoadingUrl
                    ? 'Loading stream...'
                    : urlError
                      ? 'Stream error'
                      : 'No stream available'}
                </Typography>
              </Box>
            )}
          </Box>

          {/* Remote Control Panel or Desktop Terminal */}
          {showRemote && isControlActive && (
            <Box
              sx={{
                width: (() => {
                  const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
                  return panelCount === 2 ? '20%' : '20%'; // Changed from 25% to 20% each
                })(),
                backgroundColor: 'background.default',
                borderLeft: '1px solid',
                borderColor: 'divider',
                overflow: 'auto',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
              }}
            >
              {isDesktopDevice ? (
                <DesktopPanel
                  host={host}
                  deviceId={device?.device_id || 'device1'}
                  deviceModel={device?.device_model || 'host_vnc'}
                  isConnected={isControlActive}
                  onReleaseControl={handleReleaseControl}
                  initialCollapsed={false}
                  streamContainerDimensions={finalStreamContainerDimensions}
                />
              ) : (() => {
                // Handle multiple remote controllers
                const remoteCapability = device?.device_capabilities?.remote;
                const hasMultipleRemotes = Array.isArray(remoteCapability) || device?.device_model === 'fire_tv';
                
                if (hasMultipleRemotes && device?.device_model === 'fire_tv') {
                  // For Fire TV devices, render both remotes directly (like host VNC)
                  // Account for panel overhead: header (30px) only, no disconnect button in modal
                  const panelOverhead = 30; // Header only, disconnect button removed in modal
                  const availableHeightForRemotes = finalStreamContainerDimensions.height - (panelOverhead * 2); 
                  const stackedDimensions = {
                    ...finalStreamContainerDimensions,
                    height: Math.round(availableHeightForRemotes / 2) + panelOverhead
                  };
                  return (
                    <>
                      <RemotePanel
                        host={host}
                        deviceId={device?.device_id || 'device1'}
                        deviceModel={device?.device_model || 'fire_tv'}
                        remoteType="android_tv"
                        isConnected={isControlActive}
                        onReleaseControl={handleReleaseControl}
                        initialCollapsed={false}
                        deviceResolution={stableDeviceResolution}
                        streamCollapsed={false}
                        streamMinimized={false}
                        streamContainerDimensions={stackedDimensions}
                        disableResize={true}
                      />
                      <RemotePanel
                        host={host}
                        deviceId={device?.device_id || 'device1'}
                        deviceModel={device?.device_model || 'fire_tv'}
                        remoteType="ir_remote"
                        isConnected={isControlActive}
                        onReleaseControl={handleReleaseControl}
                        initialCollapsed={false}
                        deviceResolution={stableDeviceResolution}
                        streamCollapsed={false}
                        streamMinimized={false}
                        disableResize={true}
                        streamContainerDimensions={stackedDimensions}
                      />
                    </>
                  );
                } else if (hasMultipleRemotes) {
                  // For other devices with multiple remote controllers
                  const remoteTypes = Array.isArray(remoteCapability) ? remoteCapability : [remoteCapability];
                  const filteredRemoteTypes = remoteTypes.filter(Boolean);
                  // Account for panel overhead: header (30px) only, no disconnect button in modal
                  const panelOverhead = 30; // Header only, disconnect button removed in modal
                  const availableHeightForRemotes = finalStreamContainerDimensions.height - (panelOverhead * filteredRemoteTypes.length);
                  const stackedDimensions = {
                    ...finalStreamContainerDimensions,
                    height: Math.round(availableHeightForRemotes / filteredRemoteTypes.length) + panelOverhead
                  };
                  return (
                    <>
                      {filteredRemoteTypes.map((remoteType: string) => (
                        <RemotePanel
                          key={`${device?.device_id}-${remoteType}`}
                          host={host}
                          deviceId={device?.device_id || 'device1'}
                          deviceModel={device?.device_model || 'unknown'}
                          remoteType={remoteType}
                          isConnected={isControlActive}
                          onReleaseControl={handleReleaseControl}
                          initialCollapsed={false}
                          deviceResolution={stableDeviceResolution}
                          streamCollapsed={false}
                          disableResize={true}
                          streamMinimized={false}
                          streamContainerDimensions={stackedDimensions}
                        />
                      ))}
                    </>
                  );
                } else {
                  // Single remote controller
                  return (
                    <RemotePanel
                      host={host}
                      deviceId={device?.device_id || 'device1'}
                      deviceModel={device?.device_model || 'unknown'}
                      isConnected={isControlActive}
                      onReleaseControl={handleReleaseControl}
                      initialCollapsed={false}
                      deviceResolution={stableDeviceResolution}
                      streamCollapsed={false}
                      streamMinimized={false}
                      streamContainerDimensions={finalStreamContainerDimensions}
                      disableResize={true}
                    />
                  );
                }
              })()}
            </Box>
          )}

          {/* Web Control Panel */}
          {showWeb && isControlActive && isDesktopDevice && (
            <Box
              sx={{
                width: (() => {
                  const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
                  return panelCount === 2 ? '20%' : '20%'; // Changed from 25% to 20% each
                })(),
                backgroundColor: 'background.default',
                borderLeft: '1px solid',
                borderColor: 'divider',
                overflow: 'auto',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
              }}
            >
              <WebPanel
                host={host}
                deviceId={device?.device_id || 'device1'}
                deviceModel={device?.device_model || 'host_vnc'}
                isConnected={isControlActive}
                onReleaseControl={handleReleaseControl}
                initialCollapsed={false}
                streamContainerDimensions={streamContainerDimensions}
              />
            </Box>
          )}

          {/* AI Agent Panel */}
          <AIExecutionPanel
            host={host}
            device={device!}
            isControlActive={isControlActive}
            isVisible={aiAgentMode && isControlActive}
          />
        </Box>
      </Box>
    </Box>
  );
};
