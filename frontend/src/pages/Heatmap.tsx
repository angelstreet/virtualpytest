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
  Select,
  MenuItem,
  FormControl,
} from '@mui/material';
import React, { useState, useRef } from 'react';

import { HeatMapAnalysisSection } from '../components/heatmap/HeatMapAnalysisSection';
import { HeatMapFreezeModal } from '../components/heatmap/HeatMapFreezeModal';
import { HeatMapHistory, HeatMapHistoryRef } from '../components/heatmap/HeatMapHistory';
import { MosaicPlayer } from '../components/MosaicPlayer';
import { RecHostStreamModal } from '../components/rec/RecHostStreamModal';
import { HostManagerProvider } from '../contexts/HostManagerProvider';
import { DeviceDataProvider } from '../contexts/device/DeviceDataContext';
import { useHeatmap } from '../hooks/useHeatmap';
import { useHostManager } from '../hooks/useHostManager';
import { Host, Device } from '../types/common/Host_Types';

const HeatmapContent: React.FC = () => {
  const historyRef = useRef<HeatMapHistoryRef>(null);
  const {
    timeline,
    currentIndex,
    setCurrentIndex,
    analysisData,
    hasIncidents,
    goToLatest,
    hasDataError,
    generateReport,
    getMosaicUrl,
    getFilteredDevices
  } = useHeatmap();

  // Access to real host/device data
  const { getHostByName, getDevicesFromHost } = useHostManager();

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OK' | 'KO'>('ALL');
  
  // Freeze modal state
  const [freezeModalOpen, setFreezeModalOpen] = useState(false);
  const [freezeModalData, setFreezeModalData] = useState<{
    hostName: string;
    deviceId: string;
    thumbnailUrls: string[];
    freezeDiffs: number[];
  } | null>(null);
  
  // Stream modal state
  const [streamModalOpen, setStreamModalOpen] = useState(false);
  const [streamModalHost, setStreamModalHost] = useState<Host | null>(null);
  const [streamModalDevice, setStreamModalDevice] = useState<Device | null>(null);

  // Handle freeze click from analysis table
  const handleFreezeClick = (deviceData: any) => {
    if (deviceData?.analysis_json?.freeze) {
      const analysisJson = deviceData.analysis_json;
      const r2Images = analysisJson.r2_images;
      
      // JSON is the source of truth - only use r2_images.thumbnail_urls
      const thumbnailUrls = r2Images?.thumbnail_urls || [];
      
      if (thumbnailUrls.length === 0) {
        console.warn('[@Heatmap] No R2 thumbnail URLs available for freeze - images not uploaded yet');
        return;
      }
      
      setFreezeModalData({
        hostName: deviceData.host_name || '',
        deviceId: deviceData.device_id || '',
        thumbnailUrls,
        freezeDiffs: analysisJson.freeze_diffs || []
      });
      setFreezeModalOpen(true);
    }
  };

  // Handle overlay click to open stream modal
  const handleOverlayClick = (deviceData: any) => {
    console.log('[@Heatmap] Opening stream modal for device:', deviceData);
    
    // Get real host and device data from HostManagerProvider
    const realHost = getHostByName(deviceData.host_name);
    
    if (!realHost) {
      console.error('[@Heatmap] Host not found:', deviceData.host_name);
      setError(`Host "${deviceData.host_name}" not found`);
      return;
    }
    
    // Look for the specific device in the host's devices
    const hostDevices = getDevicesFromHost(deviceData.host_name);
    const realDevice = hostDevices.find(d => d.device_id === deviceData.device_id);
    
    if (!realDevice) {
      console.error('[@Heatmap] Device not found:', deviceData.device_id, 'in host:', deviceData.host_name);
      setError(`Device "${deviceData.device_id}" not found in host "${deviceData.host_name}"`);
      return;
    }
    
    console.log('[@Heatmap] Found real host:', realHost);
    console.log('[@Heatmap] Found real device:', realDevice);
    
    // Use real data
    setStreamModalHost(realHost);
    setStreamModalDevice(realDevice);
    setStreamModalOpen(true);
  };


  // Generate report for current frame
  const handleGenerateReport = async () => {
    if (!timeline[currentIndex] || !analysisData || isGeneratingReport) return;
    
    setIsGeneratingReport(true);
    try {
      await generateReport();
      console.log('HTML report generated for frame:', timeline[currentIndex].timeKey);
      
      // Refresh history to show the new report
      if (historyRef.current) {
        await historyRef.current.refreshReports();
      }
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

      {/* Stale Data Warning */}
      {hasDataError && analysisData && (
        <MuiAlert severity="warning" sx={{ mb: 1 }}>
          ⚠️ Heatmap data may be outdated. The backend processor might not be generating new data.
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
                
                <FormControl size="small" sx={{ minWidth: 80 }}>
                  <Select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as 'ALL' | 'OK' | 'KO')}
                    sx={{ fontSize: '0.75rem', height: '24px' }}
                  >
                    <MenuItem value="ALL">ALL</MenuItem>
                    <MenuItem value="OK">OK</MenuItem>
                    <MenuItem value="KO">KO</MenuItem>
                  </Select>
                </FormControl>

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
          hasDataError={hasDataError}
          analysisData={analysisData}
          filter={filter}
          getMosaicUrl={getMosaicUrl}
        />
      </Box>

      {/* Analysis Section */}
      <Box sx={{ mb: 3 }}>
        <HeatMapAnalysisSection
          images={getFilteredDevices(analysisData?.devices || [], filter)}
          analysisExpanded={analysisExpanded}
          onToggleExpanded={() => setAnalysisExpanded(!analysisExpanded)}
          onFreezeClick={handleFreezeClick}
        />
      </Box>

      {/* History Section */}
      <HeatMapHistory ref={historyRef} />

      {/* Freeze Modal */}
      <HeatMapFreezeModal
        freezeModalOpen={freezeModalOpen}
        hostName={freezeModalData?.hostName || ''}
        deviceId={freezeModalData?.deviceId || ''}
        thumbnailUrls={freezeModalData?.thumbnailUrls || []}
        freezeDiffs={freezeModalData?.freezeDiffs || []}
        timestamp={analysisData?.timestamp}
        onClose={() => setFreezeModalOpen(false)}
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
        <HeatmapContent />
      </DeviceDataProvider>
    </HostManagerProvider>
  );
};

export default Heatmap;