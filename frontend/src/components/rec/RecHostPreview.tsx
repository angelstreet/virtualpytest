import { Error as ErrorIcon } from '@mui/icons-material';
import { Card, Typography, Box, Chip, CircularProgress } from '@mui/material';
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';

import { useModal } from '../../contexts/ModalContext';
import { useStream } from '../../hooks/controller';
import { useRec } from '../../hooks/pages/useRec';
import { useToast } from '../../hooks/useToast';
import { Host, Device } from '../../types/common/Host_Types';

import { RecHostStreamModal } from './RecHostStreamModal';

interface RecHostPreviewProps {
  host: Host;
  device?: Device;
  initializeBaseUrl?: (host: Host, device: Device) => Promise<boolean>;
  generateThumbnailUrl?: (host: Host, device: Device, timestamp?: string) => string[];
  hideHeader?: boolean;
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
  initializeBaseUrl,
  generateThumbnailUrl,
  hideHeader = false,
}) => {
  // Global modal state
  const { isAnyModalOpen } = useModal();

  // Simple 2-image state
  const [image1Url, setImage1Url] = useState<string | null>(null);
  const [image2Url, setImage2Url] = useState<string | null>(null);
  const [activeImage, setActiveImage] = useState<1 | 2>(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isStreamModalOpen, setIsStreamModalOpen] = useState(false);

  // Image queue for smooth video-like playback
  const queueRef = useRef<string[]>([]);
  const frameCounterRef = useRef<number>(0);
  const lastTimestampRef = useRef<string>('');
  const hasInitializedRef = useRef<boolean>(false);
  const startTimestampRef = useRef<string>('');

  // Detect if this is a mobile device model for proper sizing
  const isMobile = useMemo(() => {
    return isMobileModel(device?.device_model);
  }, [device?.device_model]);

  // Check if this is a VNC device
  const isVncDevice = useMemo(() => {
    return device?.device_model === 'host_vnc';
  }, [device?.device_model]);

  // For VNC devices, get the stream URL directly
  const { streamUrl: vncStreamUrl } = useStream({
    host,
    device_id: device?.device_id || 'device1',
  });

  // Get VNC scaling function from useRec
  const { calculateVncScaling } = useRec();

  // Hook for notifications only
  const { showError } = useToast();

  // Stabilize host and device objects to prevent infinite re-renders
  const stableHost = useMemo(() => host, [host]);
  const stableDevice = useMemo(() => device, [device]);
  const stableHostRef = useRef(stableHost);
  const stableDeviceRef = useRef(stableDevice);

  useEffect(() => {
    stableHostRef.current = stableHost;
    stableDeviceRef.current = stableDevice;
  }, [stableHost, stableDevice]);

  // Handle when an image loads successfully
  const handleImageLoad = useCallback((imageNumber: 1 | 2) => {
    const currentUrl = imageNumber === 1 ? image1Url : image2Url;
    console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] DISPLAYING image ${imageNumber}: ${currentUrl}`);
    setActiveImage(imageNumber); // Switch to the newly loaded image
  }, [image1Url, image2Url, stableHost.host_name, stableDevice?.device_id]);

  // Process screenshot URL with conditional HTTP to HTTPS proxy
  const getImageUrl = useCallback((screenshotPath: string) => screenshotPath || '', []);

  // Generate next expected frame URL
  const generateNextFrameUrl = useCallback(() => {
    if (!generateThumbnailUrl || !stableDevice) return null;

    // Use sequential timestamps starting from the captured start time
    let currentTimestamp = lastTimestampRef.current;
    
    // Initialize with start timestamp if not set
    if (!currentTimestamp && startTimestampRef.current) {
      currentTimestamp = startTimestampRef.current;
      lastTimestampRef.current = currentTimestamp;
      frameCounterRef.current = 0;
    }
    
    // If still no timestamp, return null (not ready yet)
    if (!currentTimestamp) {
      return null;
    }
    
    // Move to next timestamp when we've cycled through all 5 frames (0-4)
    if (frameCounterRef.current >= 5) {
      const lastTime = new Date();
      lastTime.setTime(Date.parse(
        currentTimestamp.slice(0,4) + '-' + 
        currentTimestamp.slice(4,6) + '-' + 
        currentTimestamp.slice(6,8) + 'T' + 
        currentTimestamp.slice(8,10) + ':' + 
        currentTimestamp.slice(10,12) + ':' + 
        currentTimestamp.slice(12,14)
      ));
      lastTime.setSeconds(lastTime.getSeconds() + 1); // Next second
      
      currentTimestamp = 
        lastTime.getFullYear().toString() +
        (lastTime.getMonth() + 1).toString().padStart(2, '0') +
        lastTime.getDate().toString().padStart(2, '0') +
        lastTime.getHours().toString().padStart(2, '0') +
        lastTime.getMinutes().toString().padStart(2, '0') +
        lastTime.getSeconds().toString().padStart(2, '0');
      
      lastTimestampRef.current = currentTimestamp;
      frameCounterRef.current = 0;
    }

    // Generate URL for current frame (0-4, then cycle)
    const frameNum = frameCounterRef.current % 5;
    const frameSuffix = frameNum === 0 ? '' : `_${frameNum}`;
    
    // Increment for next call
    frameCounterRef.current++;

    const baseUrl = generateThumbnailUrl(stableHost, stableDevice, currentTimestamp)[0]?.replace('_thumbnail.jpg', '') || '';
    const finalUrl = `${baseUrl}${frameSuffix}_thumbnail.jpg`;
    
    // Log the timestamp being used for verification
    console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] Using timestamp ${currentTimestamp} for frame ${frameNum}: ${finalUrl}`);
    
    return finalUrl;
  }, [stableHost, stableDevice, generateThumbnailUrl]);

  // Single loop: preload next frame + display queued frame
  const processNextFrame = useCallback(async () => {
    if (isVncDevice || isAnyModalOpen) return;

    // Try to preload next expected frame
    const nextFrameUrl = generateNextFrameUrl();
    if (nextFrameUrl) {
      try {
        await new Promise((resolve, reject) => {
          const img = new Image();
          img.onload = () => resolve(nextFrameUrl);
          img.onerror = reject;
          img.src = nextFrameUrl;
        });
        
        // Add to queue (keep max 5 frames)
        queueRef.current = [...queueRef.current, nextFrameUrl].slice(-5);
      } catch {
        // Frame not ready yet, skip silently
      }
    }

    // Display next frame from queue if available
    if (queueRef.current.length > 0) {
      const nextUrl = queueRef.current[0];
      queueRef.current = queueRef.current.slice(1);
      
      // Get current activeImage value and set the appropriate image URL
      let currentActiveImage: 1 | 2;
      setActiveImage(current => {
        currentActiveImage = current;
        return current; // Don't change activeImage here, let handleImageLoad do it
      });
      
      // Set the image URL outside the state updater to prevent multiple calls
      if (currentActiveImage! === 1) {
        console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] SETTING image2Url: ${nextUrl}`);
        setImage2Url(nextUrl);
      } else {
        console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] SETTING image1Url: ${nextUrl}`);
        setImage1Url(nextUrl);
      }
    }
  }, [isVncDevice, isAnyModalOpen, generateNextFrameUrl]);

  // Single loop - matches ffmpeg generation timing (200ms)
  useEffect(() => {
    console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] Component mounted`);
    return () => console.log(`[${stableHost.host_name}-${stableDevice?.device_id}] Component unmounted`);
  }, []);

  // Single loop - matches ffmpeg generation timing (200ms)
  useEffect(() => {
    let isMounted = true;

    const startSystem = async () => {
      const currentHost = stableHostRef.current;
      const currentDevice = stableDeviceRef.current;

      if (isVncDevice || isStreamModalOpen || isAnyModalOpen) return;
      if (!currentHost || !currentDevice || !initializeBaseUrl) return;

      // Initialize base URL once
      const initialized = await initializeBaseUrl(currentHost, currentDevice);
      if (!initialized || !isMounted) {
        if (isMounted) setError('Failed to initialize base URL');
        return;
      }

      // Initial delay only on first initialization
      if (!hasInitializedRef.current) {
        // Capture timestamp BEFORE waiting to maintain constant delay
        const now = new Date();
        startTimestampRef.current = 
          now.getFullYear().toString() +
          (now.getMonth() + 1).toString().padStart(2, '0') +
          now.getDate().toString().padStart(2, '0') +
          now.getHours().toString().padStart(2, '0') +
          now.getMinutes().toString().padStart(2, '0') +
          now.getSeconds().toString().padStart(2, '0');
        
        // Initialize lastTimestampRef with the start timestamp immediately
        lastTimestampRef.current = startTimestampRef.current;
        frameCounterRef.current = 0;
        
        setIsLoading(true);
        console.log(`[${currentHost.host_name}-${currentDevice?.device_id}] Starting 1.5s wait for timestamp ${startTimestampRef.current}...`);
        console.log(`[${currentHost.host_name}-${currentDevice?.device_id}] Initialized lastTimestampRef to: ${lastTimestampRef.current}`);
        await new Promise(resolve => setTimeout(resolve, 1500));
        hasInitializedRef.current = true;
        if (isMounted) setIsLoading(false);
      }

      // Single 200ms loop matching ffmpeg generation
      const frameInterval = setInterval(() => {
        if (isMounted && !isStreamModalOpen && !isAnyModalOpen) {
          processNextFrame();
        }
      }, 200);

      return () => clearInterval(frameInterval);
    };

    const cleanup = startSystem();

    return () => {
      isMounted = false;
      cleanup.then(fn => fn?.());
    };
  }, []);  // Empty dependencies to run only once on mount





  // Handle opening stream modal
  const handleOpenStreamModal = useCallback(() => {
    // Basic check if host is online
    if (stableHost.status !== 'online') {
      showError('Host is not online');
      return;
    }

    // Just open the modal - let it handle control logic
    setIsStreamModalOpen(true);
  }, [stableHost, showError]);

  // Handle closing stream modal
  const handleCloseStreamModal = useCallback(() => {
    setIsStreamModalOpen(false);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'error';
      default:
        return 'default';
    }
  };

  // Clean display values - special handling for VNC devices
  const displayName = stableDevice
    ? stableDevice.device_model === 'host_vnc'
      ? stableHost.host_name // For VNC devices, show just the host name
      : `${stableDevice.device_name} - ${stableHost.host_name}`
    : stableHost.host_name;

  return (
    <Card
      sx={{
        height: 200,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        p: 0,
        backgroundColor: 'transparent',
        backgroundImage: 'none',
        boxShadow: 'none',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        '&:hover': {
          boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
        },
        '& .MuiCard-root': {
          padding: 0,
        },
      }}
    >
      {/* Header */}
      {!hideHeader && (
        <Box
          sx={{
            px: 1,
            py: 0.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Typography variant="subtitle2" noWrap sx={{ flex: 1, mr: 1 }}>
            {displayName}
          </Typography>
          <Chip
            label={stableHost.status}
            size="small"
            color={getStatusColor(stableHost.status) as any}
            sx={{ fontSize: '0.7rem', height: 20 }}
          />
        </Box>
      )}

      {/* Content area - VNC iframe or screenshot */}
      <Box sx={{ flex: 1, position: 'relative', minHeight: 0, overflow: 'hidden' }}>
        <Box
          sx={{
            height: '100%',
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: 'transparent',
          }}
        >
          {/* VNC devices: Show iframe preview */}
          {isVncDevice ? (
            vncStreamUrl ? (
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
                  src={vncStreamUrl}
                  style={{
                    border: 'none',
                    backgroundColor: '#000',
                    pointerEvents: 'none',
                    ...calculateVncScaling({ width: 300, height: 150 }), // Preview card target size
                  }}
                  title="VNC Desktop Preview"
                />
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
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.1)',
                    },
                  }}
                />
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
                  Loading VNC stream...
                </Typography>
              </Box>
            )
          ) : (
            // Non-VNC devices: Show screenshot thumbnails with simple 2-image algorithm
            <>
              {error ? (
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
              ) : image1Url || image2Url ? (
                <Box
                  sx={{
                    position: 'relative',
                    width: '100%',
                    height: '100%',
                    backgroundColor: 'transparent',
                    overflow: 'hidden',
                  }}
                >
                  {/* Image 1 */}
                  {image1Url && (
                    <Box
                      component="img"
                      src={getImageUrl(image1Url)}
                      alt="Screenshot 1"
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: isMobile ? 'auto' : '100%',
                        height: isMobile ? '100%' : 'auto',
                        objectFit: 'contain',
                        opacity: activeImage === 1 ? 1 : 0,
                        cursor: 'pointer',
                      }}
                      draggable={false}
                      onLoad={() => handleImageLoad(1)}
                      onError={() => {
                        // console.log(
                        //   `[RecHostPreview] Image 1 failed to load: ${image1Url} - keeping current image`,
                        // );
                        // Do nothing - keep current active image
                      }}
                    />
                  )}

                  {/* Image 2 */}
                  {image2Url && (
                    <Box
                      component="img"
                      src={getImageUrl(image2Url)}
                      alt="Screenshot 2"
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: isMobile ? 'auto' : '100%',
                        height: isMobile ? '100%' : 'auto',
                        objectFit: 'contain',
                        opacity: activeImage === 2 ? 1 : 0,
                        cursor: 'pointer',
                      }}
                      draggable={false}
                      onLoad={() => handleImageLoad(2)}
                      onError={() => {
                        // console.log(
                        //   `[RecHostPreview] Image 2 failed to load: ${image2Url} - keeping current image`,
                        // );
                        // Do nothing - keep current active image
                      }}
                    />
                  )}

                  {/* Click overlay to open stream modal */}
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
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                      },
                    }}
                  />
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
                  {isLoading ? (
                    <>
                      <CircularProgress size={24} />
                      <Typography variant="caption" color="text.secondary">
                        Capturing screenshot...
                      </Typography>
                    </>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      No screenshot available
                    </Typography>
                  )}
                </Box>
              )}
            </>
          )}
        </Box>
      </Box>

      {/* Stream Modal */}
      <RecHostStreamModal
        host={stableHost}
        device={stableDevice}
        isOpen={isStreamModalOpen}
        onClose={handleCloseStreamModal}
      />
    </Card>
  );
};
