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
  generateThumbnailUrl?: (host: Host, device: Device) => string[];
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

  // Get VNC scaling function and adaptive interval from useRec
  const { calculateVncScaling, adaptiveInterval } = useRec();

  // Hook for notifications only
  const { showError } = useToast();

  // Stabilize host and device objects to prevent infinite re-renders
  const stableHost = useMemo(() => host, [host]);
  const stableDevice = useMemo(() => device, [device]);

  // Handle when an image loads successfully
  const handleImageLoad = useCallback((imageNumber: 1 | 2) => {
    setActiveImage(imageNumber); // Switch to the newly loaded image
  }, []);

  // Process screenshot URL with conditional HTTP to HTTPS proxy
  const getImageUrl = useCallback((screenshotPath: string) => screenshotPath || '', []);

  // Queue refill logic
  const refillQueue = useCallback(async () => {
    if (isVncDevice || isAnyModalOpen || !generateThumbnailUrl || !stableDevice) return;

    const frameUrls = generateThumbnailUrl(stableHost, stableDevice);
    if (frameUrls.length === 0) return;

    // Preload images in parallel, then sort successful ones by frame order
    const preloadPromises = frameUrls.map((url, index) => 
      new Promise((resolve, reject) => {
        const tryLoad = (attempt = 0) => {
          const img = new Image();
          img.onload = () => resolve(url);
          img.onerror = () => {
            if (attempt < 1 && index <= 2) { // Retry once for early frames
              setTimeout(() => tryLoad(attempt + 1), 100);
            } else {
              reject();
            }
          };
          img.src = url;
        };
        tryLoad();
      })
    );

    const results = await Promise.allSettled(preloadPromises);
    const validUrls = results
      .filter(result => result.status === 'fulfilled')
      .map(result => result.value as string)
      .sort((a, b) => {
        const frameA = parseInt(a.match(/_(\d+)_thumbnail/)?.[1] || '0');
        const frameB = parseInt(b.match(/_(\d+)_thumbnail/)?.[1] || '0');
        return frameA - frameB;
      });
    
    if (validUrls.length > 0) {
      // Extract timestamp from first valid URL (e.g., '20250901182649' from 'capture_20250901182649_thumbnail.jpg')
      const getTimestamp = (url: string) => url.match(/capture_(\d{14})/)?.[1] || '0';

      const newTimestamp = getTimestamp(validUrls[0]);
      const currentTimestamp = queueRef.current.length > 0 ? getTimestamp(queueRef.current[0]) : '0';

      // Replace if new batch is newer or queue is low
      if (newTimestamp > currentTimestamp || queueRef.current.length <= 1) {
        queueRef.current = validUrls;
      }
    }
  }, [stableHost, stableDevice, generateThumbnailUrl, isAnyModalOpen, isVncDevice]);

  // Display loop - consume queue every 200ms
  useEffect(() => {
    if (isVncDevice) return;

    const displayInterval = setInterval(() => {
      if (queueRef.current.length > 0) {
        const nextUrl = queueRef.current[0]; // Peek at first frame
        queueRef.current = queueRef.current.slice(1); // Remove after using
        
        if (activeImage === 1) {
          setImage2Url(nextUrl);
        } else {
          setImage1Url(nextUrl);
        }
      }
    }, 200);

    return () => clearInterval(displayInterval);
  }, [activeImage, isVncDevice]);

  // Queue refill loop - adaptive timing
  useEffect(() => {
    if (isVncDevice || isStreamModalOpen || isAnyModalOpen) return;
    if (!stableHost || !stableDevice || !initializeBaseUrl) return;

    let isMounted = true;

    const startSystem = async () => {
      // Initialize base URL once
      const initialized = await initializeBaseUrl(stableHost, stableDevice);
      if (!initialized || !isMounted) {
        if (isMounted) setError('Failed to initialize base URL');
        return;
      }

      // Initial queue fill
      setIsLoading(true);
      await refillQueue();
      if (isMounted) setIsLoading(false);

      // Set up adaptive refill interval
      const refillInterval = setInterval(() => {
        if (isMounted && !isStreamModalOpen && !isAnyModalOpen) {
          refillQueue();
        }
      }, adaptiveInterval);

      return () => clearInterval(refillInterval);
    };

    const cleanup = startSystem();

    return () => {
      isMounted = false;
      cleanup.then(fn => fn?.());
    };
  }, [stableHost, stableDevice, initializeBaseUrl, refillQueue, adaptiveInterval, isStreamModalOpen, isAnyModalOpen, isVncDevice, setError, setIsLoading]);





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
