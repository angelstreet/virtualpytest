import { Error as ErrorIcon } from '@mui/icons-material';
import { Card, Typography, Box, Chip, CircularProgress, Checkbox } from '@mui/material';
import React, { useState, useCallback, useMemo, useEffect } from 'react';

import { DEFAULT_DEVICE_RESOLUTION } from '../../config/deviceResolutions';
import { useStream } from '../../hooks/controller';
import { useToast } from '../../hooks/useToast';
import { Host, Device } from '../../types/common/Host_Types';
import { calculateVncScaling } from '../../utils/vncUtils';
import { EnhancedHLSPlayer } from '../video/EnhancedHLSPlayer';

interface RecHostPreviewProps {
  host: Host;
  device?: Device;
  hideHeader?: boolean;
  isEditMode?: boolean;
  isSelected?: boolean;
  onSelectionChange?: (selected: boolean) => void;
  deviceFlags?: string[];
  onOpenModal?: () => void;
  isAnyModalOpen?: boolean;
  isSelectedForModal?: boolean;
  onStreamActiveChange?: (isActive: boolean) => void;
  sharedVideoRef?: React.RefObject<HTMLVideoElement>;
  showFullFeatures?: boolean; // Show timeline and all overlays when modal is open
  
  // Modal control props - passed when modal is open
  modalIsLiveMode?: boolean;
  modalQuality?: 'low' | 'sd' | 'hd';
  modalMuted?: boolean;
  onPlayerReady?: () => void;
  onVideoTimeUpdate?: (time: number) => void;
}

// Simple mobile detection function to match MonitoringPlayer logic
const isMobileModel = (model?: string): boolean => {
  if (!model) return false;
  const modelLower = model.toLowerCase();
  return modelLower.includes('mobile');
};

export const RecHostPreview: React.FC<RecHostPreviewProps> = ({
  host,
  device,
  hideHeader = false,
  isEditMode = false,
  isSelected = false,
  onSelectionChange,
  deviceFlags = [],
  onOpenModal,
  isAnyModalOpen,
  isSelectedForModal,
  onStreamActiveChange,
  sharedVideoRef,
  showFullFeatures = false,
  modalIsLiveMode = true,
  modalQuality = 'low',
  modalMuted = false,
  onPlayerReady,
  onVideoTimeUpdate,
}) => {
  useEffect(() => {
    console.log('[@RecHostPreview] mounted', {
      host: host.host_name,
      deviceId: device?.device_id,
    });
    return () => {
      console.log('[@RecHostPreview] unmounted', {
        host: host.host_name,
        deviceId: device?.device_id,
      });
    };
  }, [host.host_name, device?.device_id]);

  useEffect(() => {
    console.log('[@RecHostPreview] render', {
      host: host.host_name,
      deviceId: device?.device_id,
      isEditMode,
      isSelected,
      deviceFlags,
    });
  });

  // States
  const [error] = useState<string | null>(null);
  const [isStreamActive, setIsStreamActive] = useState(true);

  useEffect(() => {
    onStreamActiveChange?.(isStreamActive);
  }, [isStreamActive, onStreamActiveChange]);

  // Detect if this is a mobile device model for proper sizing
  const isMobile = useMemo(() => {
  return isMobileModel(device?.device_model);
}, [device?.device_model]);

  // Check if this is a VNC device
  const isVncDevice = useMemo(() => {
    return device?.device_model === 'host_vnc';
  }, [device?.device_model]);

  // Use stream hook for all devices (VNC gets VNC URL, others get HLS URL)
  const { streamUrl } = useStream({
    host,
    device_id: device?.device_id || 'device1',
  });

  // Memoize layout config to prevent unnecessary re-renders
  const layoutConfig = useMemo(() => ({
    minHeight: '150px',
    aspectRatio: isMobile 
      ? `${DEFAULT_DEVICE_RESOLUTION.height}/${DEFAULT_DEVICE_RESOLUTION.width}` 
      : `${DEFAULT_DEVICE_RESOLUTION.width}/${DEFAULT_DEVICE_RESOLUTION.height}`,
    objectFit: (isMobile ? 'fill' : 'contain') as 'fill' | 'contain' | 'cover',
    isMobileModel: isMobile,
  }), [isMobile]);

  // Device flags are now passed as props from parent

  // Hook for notifications
  const { showError } = useToast();

  // Cleanup stream when component unmounts
  useEffect(() => {
    return () => {
      console.log('[@component:RecHostPreview] Component unmounting, stopping stream');
      setIsStreamActive(false);
    };
  }, []);

  useEffect(() => {
    const shouldPauseThisDevice = isAnyModalOpen && !isSelectedForModal;
    setIsStreamActive(!shouldPauseThisDevice);
    console.log(`[@RecHostPreview] Stream ${shouldPauseThisDevice ? 'paused' : 'active'} for ${host.host_name}-${device?.device_id} (modal open=${isAnyModalOpen}, selected=${isSelectedForModal})`);
  }, [isAnyModalOpen, isSelectedForModal, host.host_name, device?.device_id]);


  // Handle opening/closing with restored state
  const handleOpenStreamModal = useCallback(() => {
    if (host.status !== 'online') {
      showError('Host is not online');
      return;
    }
    console.log('[@RecHostPreview] Opening modal - stopping preview stream');
    setIsStreamActive(false); // Stop preview stream when opening modal
    onOpenModal?.();
  }, [host, showError, onOpenModal]);

  const getStatusColor = (status: string, isStuck: boolean = false) => {
    // If processes are stuck, always show error regardless of host status
    if (isStuck) {
      return 'error';
    }
    
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'error';
      default:
        return 'default';
    }
  };

  // Check if host has stuck processes
  const isHostStuck = useMemo(() => {
    const ffmpegStuck = host.system_stats?.ffmpeg_status?.status === 'stuck';
    const monitorStuck = host.system_stats?.monitor_status?.status === 'stuck';
    return ffmpegStuck || monitorStuck;
  }, [host.system_stats?.ffmpeg_status?.status, host.system_stats?.monitor_status?.status]);

  // Clean display values - special handling for VNC devices
  const displayName = device
    ? device.device_model === 'host_vnc'
      ? host.host_name // For VNC devices, show just the host name
      : `${device.device_name} - ${host.host_name}`
    : host.host_name;

  const isPausingForModal = Boolean(isAnyModalOpen);
  const pauseMessage = isSelectedForModal ? 'Playing in modal' : 'Preview paused';

  return (
    <Card
      sx={{
        height: showFullFeatures ? '100vh' : 180,
        width: showFullFeatures ? '100vw' : '100%',
        display: 'flex',
        flexDirection: 'column',
        position: showFullFeatures ? 'fixed' : 'relative',
        top: showFullFeatures ? 0 : 'auto',
        left: showFullFeatures ? 0 : 'auto',
        zIndex: showFullFeatures ? 1200 : 'auto', // Below modal controls (1300)
        p: 0,
        backgroundColor: showFullFeatures ? 'black' : 'transparent',
        backgroundImage: 'none',
        boxShadow: 'none',
        border: showFullFeatures ? 'none' : (isSelected ? '2px solid #1976d2' : '1px solid rgba(255, 255, 255, 0.1)'),
        '&:hover': {
          boxShadow: showFullFeatures ? 'none' : '0px 4px 20px rgba(0, 0, 0, 0.3)',
          border: showFullFeatures ? 'none' : (isSelected ? '2px solid #1976d2' : '1px solid rgba(255, 255, 255, 0.2)'),
        },
        '& .MuiCard-root': {
          padding: 0,
        },
      }}
    >
      {/* Header - hidden in fullscreen mode (modal has its own) */}
      {!hideHeader && !showFullFeatures && (
        <Box
          sx={{
            px: 1,
            py: 0.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 0.5,
            position: 'relative',
          }}
        >
          <Typography variant="subtitle2" noWrap sx={{ flex: 1, mr: 1, minWidth: 0 }}>
            {displayName}
          </Typography>
          
          {/* Device flags - simple display */}
          {deviceFlags.slice(0, 2).map((flag) => (
            <Chip
              key={flag}
              label={flag}
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.65rem', height: 18, maxWidth: 60 }}
            />
          ))}
          
          {/* More flags indicator */}
          {deviceFlags.length > 2 && (
            <Chip
              label={`+${deviceFlags.length - 2}`}
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.6rem', height: 16, minWidth: 20 }}
            />
          )}
          
          {/* Selection checkbox in edit mode - positioned before status chip */}
          {isEditMode && (
            <Checkbox
              size="small"
              checked={isSelected}
              onChange={(e) => onSelectionChange?.(e.target.checked)}
              sx={{ 
                p: 0.5,
                '& .MuiSvgIcon-root': {
                  fontSize: '1rem'
                }
              }}
            />
          )}
          
          {/* Status chip */}
          <Chip
            label={isHostStuck ? 'error' : host.status}
            size="small"
            color={getStatusColor(host.status, isHostStuck) as any}
            sx={{ fontSize: '0.7rem', height: 20 }}
          />
        </Box>
      )}

      {/* Content area - Stream preview */}
      <Box sx={{ flex: 1, position: 'relative', minHeight: 0, overflow: 'hidden' }}>
        <Box
          sx={{
            height: '100%',
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: 'black',
          }}
        >
          {streamUrl ? (
            isVncDevice ? (
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
                    pointerEvents: 'none',
                    ...calculateVncScaling({ width: 300, height: 150 }), // Preview card target size
                  }}
                  title="VNC Desktop Preview"
                />
                {/* Pause overlay when modal is open */}
                {isPausingForModal && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: 'rgba(0, 0, 0, 0.85)',
                      zIndex: 2,
                    }}
                  >
                    <Typography variant="caption" align="center" sx={{ color: 'grey.500' }}>
                      {pauseMessage}
                    </Typography>
                  </Box>
                )}
                {/* Click overlay to open full modal */}
                <Box
                  onClick={handleOpenStreamModal}
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    zIndex: 1,
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.1)',
                    },
                  }}
                />
              </Box>
            ) : (
              <Box
                sx={{
                  position: 'relative',
                  width: '100%',
                  height: '100%',
                  backgroundColor: 'black',
                  overflow: 'hidden',
                }}
              >
                <EnhancedHLSPlayer
                  deviceId={device?.device_id || 'device1'}
                  hostName={host.host_name}
                  host={host}
                  streamUrl={streamUrl}
                  width="100%"
                  height={isMobile ? 600 : 400}
                  muted={showFullFeatures ? modalMuted : true}
                  isLiveMode={showFullFeatures ? modalIsLiveMode : true}
                  quality={showFullFeatures ? modalQuality : 'low'}
                  shouldPause={!isStreamActive}
                  videoElementRef={sharedVideoRef}
                  onPlayerReady={showFullFeatures ? onPlayerReady : undefined}
                  onVideoTimeUpdate={showFullFeatures ? onVideoTimeUpdate : undefined}
                  showTimeline={showFullFeatures}
                  showMonitoringOverlay={false}
                />
                {!showFullFeatures && isPausingForModal && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: 'rgba(0, 0, 0, 0.85)',
                      zIndex: 2,
                    }}
                  >
                    <Typography variant="caption" align="center" sx={{ color: 'grey.500' }}>
                      {pauseMessage}
                    </Typography>
                  </Box>
                )}
                {!showFullFeatures && (
                  <Box
                    onClick={handleOpenStreamModal}
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      cursor: 'pointer',
                      backgroundColor: 'transparent',
                      zIndex: 1,
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                      },
                    }}
                  />
                )}
              </Box>
            )
          ) : error ? (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'error.main',
              }}
            >
              <ErrorIcon sx={{ mb: 1 }} />
              <Typography variant="caption" align="center">
                {error}
              </Typography>
            </Box>
          ) : (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 2,
              }}
            >
              <CircularProgress size={24} />
              <Typography variant="caption" color="text.secondary">
                Loading stream...
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Stream Modal */}
      {/* The RecHostStreamModal component is no longer rendered here */}
    </Card>
  );
};
