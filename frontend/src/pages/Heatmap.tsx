import {
  GridView as HeatmapIcon,
  OpenInNew,
  GridView,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Alert as MuiAlert,
  Tooltip,
  IconButton,
} from '@mui/material';
import React, { useState } from 'react';

import { HeatMapAnalysisSection } from '../components/heatmap/HeatMapAnalysisSection';
import { HeatMapFreezeModal } from '../components/heatmap/HeatMapFreezeModal';
import { HeatMapHistory } from '../components/heatmap/HeatMapHistory';
import { MosaicPlayer } from '../components/MosaicPlayer';
import { RecHostStreamModal } from '../components/rec/RecHostStreamModal';
import { ModalProvider } from '../contexts/ModalContext';
import { HostManagerProvider } from '../contexts/HostManagerProvider';
import { DeviceDataProvider } from '../contexts/device/DeviceDataContext';
import { useHeatmap } from '../hooks/useHeatmap';
import { useHostManager } from '../hooks/useHostManager';
import { Host, Device } from '../types/common/Host_Types';

const HeatmapContent: React.FC = () => {
  const {
    timeline,
    currentIndex,
    setCurrentIndex,
    analysisData,
    analysisLoading,
    hasIncidents,
    goToLatest,
    hasDataError,
    generateReport
  } = useHeatmap();

  // Access to real host/device data
  const { getHostByName, getDevicesFromHost } = useHostManager();

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  
  // Freeze modal state
  const [freezeModalOpen, setFreezeModalOpen] = useState(false);
  const [freezeModalImage, setFreezeModalImage] = useState<any>(null);
  
  // Stream modal state
  const [streamModalOpen, setStreamModalOpen] = useState(false);
  const [streamModalHost, setStreamModalHost] = useState<Host | null>(null);
  const [streamModalDevice, setStreamModalDevice] = useState<Device | null>(null);

  // Handle freeze click from analysis table
  const handleFreezeClick = (deviceData: any) => {
    if (deviceData?.analysis_json?.freeze) {
      setFreezeModalImage(deviceData);
      setFreezeModalOpen(true);
    }
  };

  // Handle overlay click to open stream modal
  const handleOverlayClick = (deviceData: any) => {
    console.log('[@Heatmap] Opening stream modal for device:', deviceData);
    
    // Try to get real host and device data from HostManagerProvider
    const realHost = getHostByName(deviceData.host_name);
    let realDevice: Device | null = null;
    
    if (realHost) {
      // Look for the specific device in the host's devices
      const hostDevices = getDevicesFromHost(deviceData.host_name);
      realDevice = hostDevices.find(d => d.device_id === deviceData.device_id) || null;
      
      console.log('[@Heatmap] Found real host:', realHost);
      console.log('[@Heatmap] Found real device:', realDevice);
      
      if (realDevice) {
        // Use real data
        setStreamModalHost(realHost);
        setStreamModalDevice(realDevice);
        setStreamModalOpen(true);
        return;
      }
    }
    
    // Fallback: Create mock data if real data not available
    console.log('[@Heatmap] Real device data not found, using fallback mock data');
    
    const fallbackDevice: Device = {
      device_id: deviceData.device_id,
      device_name: deviceData.device_name || deviceData.device_id,
      device_model: 'android_mobile', // Default fallback - will show appropriate remote
      device_capabilities: {
        av: 'hdmi_stream',
        remote: 'android_mobile', // Match the device model
        power: 'adb'
      }
    };

    const fallbackHost: Host = {
      host_name: deviceData.host_name,
      host_url: `http://${deviceData.host_name}:6109`,
      host_port: 6109,
      devices: [fallbackDevice],
      device_count: 1,
      status: 'online',
      last_seen: Date.now(),
      registered_at: new Date().toISOString(),
      system_stats: {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        platform: 'linux',
        architecture: 'x86_64',
        python_version: '3.9'
      },
      isLocked: false
    };

    setStreamModalHost(fallbackHost);
    setStreamModalDevice(fallbackDevice);
    setStreamModalOpen(true);
  };

  // Helper function to construct frame URLs
  const constructFrameUrl = (filename: string, originalImageUrl: string): string => {
    // Handle full paths from last_3_filenames (e.g., "/path/to/captures/capture_370348.jpg")
    const cleanFilename = filename.includes('/') ? filename.split('/').pop() || filename : filename;
    
    // Get base URL from original image URL
    const lastSlashIndex = originalImageUrl.lastIndexOf('/');
    if (lastSlashIndex === -1) return cleanFilename;
    const baseUrl = originalImageUrl.substring(0, lastSlashIndex + 1);
    
    // Construct the full URL
    const frameUrl = `${baseUrl}${cleanFilename}`;
    console.log(`[@HeatMapFreezeModal] Constructing frame URL: ${filename} -> ${frameUrl}`);
    return frameUrl;
  };

  // Generate report for current frame
  const handleGenerateReport = async () => {
    if (!timeline[currentIndex] || !analysisData || isGeneratingReport) return;
    
    setIsGeneratingReport(true);
    try {
      await generateReport();
      console.log('HTML report generated for frame:', timeline[currentIndex].timeKey);
    } catch (error) {
      console.error('Error generating report:', error);
      setError('Failed to generate report');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <Box>
      {error && (
        <MuiAlert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </MuiAlert>
      )}

      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <HeatmapIcon color="primary" />
                <Typography variant="h6">24h Heatmap</Typography>
                {timeline[currentIndex] && (
                  <Typography variant="body2" sx={{ ml: 2, color: 'text.primary' }}>
                    {timeline[currentIndex].isToday ? 'Today' : 'Yesterday'} {timeline[currentIndex].displayTime.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                )}
                <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
                  Frame {currentIndex + 1} / {timeline.length}
                </Typography>
                {hasIncidents() && (
                  <Typography variant="body2" sx={{ ml: 2, color: 'error.main', fontWeight: 'bold' }}>
                    Incidents Detected
                  </Typography>
                )}
              </Box>

              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Devices</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {analysisData?.hosts_count || 0}
                  </Typography>
                </Box>
                
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Status</Typography>
                  <Typography variant="body2" fontWeight="bold" color={hasIncidents() ? 'error' : 'success'}>
                    {hasIncidents() ? 'KO' : 'OK'}
                  </Typography>
                </Box>

                {/* Go to Latest Button */}
                <Tooltip title="Go to Latest">
                  <IconButton size="small" onClick={goToLatest}>
                    <OpenInNew />
                  </IconButton>
                </Tooltip>
                
                {/* Generate Report Button */}
                <Tooltip title="Generate Report for Current Frame">
                  <IconButton 
                    size="small" 
                    onClick={handleGenerateReport}
                    disabled={isGeneratingReport || !analysisData || !timeline[currentIndex]}
                  >
                    <GridView />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Mosaic Player */}
      <Box sx={{ mb: 3 }}>
        <MosaicPlayer
          timeline={timeline}
          currentIndex={currentIndex}
          onIndexChange={setCurrentIndex}
          onCellClick={handleOverlayClick}
          hasIncidents={hasIncidents()}
          isLoading={analysisLoading}
          hasDataError={hasDataError}
          analysisData={analysisData}
        />
      </Box>

      {/* Analysis Section */}
      <Box sx={{ mb: 3 }}>
        <HeatMapAnalysisSection
          images={analysisData?.devices || []}
          analysisExpanded={analysisExpanded}
          onToggleExpanded={() => setAnalysisExpanded(!analysisExpanded)}
          onFreezeClick={handleFreezeClick}
        />
      </Box>

      {/* History Section */}
      <HeatMapHistory />

      {/* Freeze Modal */}
      <HeatMapFreezeModal
        freezeModalOpen={freezeModalOpen}
        freezeModalImage={freezeModalImage}
        onClose={() => setFreezeModalOpen(false)}
        constructFrameUrl={constructFrameUrl}
        timestamp={analysisData?.timestamp}
      />

      {/* Stream Modal */}
      {streamModalHost && streamModalDevice && (
        <RecHostStreamModal
          host={streamModalHost}
          device={streamModalDevice}
          isOpen={streamModalOpen}
          onClose={() => {
            setStreamModalOpen(false);
            setStreamModalHost(null);
            setStreamModalDevice(null);
          }}
          showRemoteByDefault={false}
        />
      )}
    </Box>
  );
};

const Heatmap: React.FC = () => {
  return (
    <HostManagerProvider>
      <DeviceDataProvider>
        <ModalProvider>
          <HeatmapContent />
        </ModalProvider>
      </DeviceDataProvider>
    </HostManagerProvider>
  );
};

export default Heatmap;