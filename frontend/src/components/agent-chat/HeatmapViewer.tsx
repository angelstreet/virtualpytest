/**
 * Heatmap Viewer - Embedded heatmap visualization for AgentChat
 *
 * Shows only the top part of the heatmap page: header + mosaic player (timeline + visualization)
 * Excludes data analysis and history sections for clean viewing in ContentViewer.
 */

import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  Tooltip,
} from '@mui/material';
import {
  GridView as HeatmapIcon,
  OpenInNew,
  GridView,
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

import { HostManagerProvider } from '../../contexts/HostManagerProvider';
import { DeviceDataProvider } from '../../contexts/device/DeviceDataContext';
import { MosaicPlayer } from '../../components/MosaicPlayer';
import { RecHostStreamModal } from '../../components/rec/RecHostStreamModal';
import { useHeatmap } from '../../hooks/useHeatmap';
import { useHostManager } from '../../hooks/useHostManager';
import { Host, Device } from '../../types/common/Host_Types';

const HeatmapViewerContent: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';

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
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OK' | 'KO'>('ALL');

  // Stream modal state
  const [streamModalOpen, setStreamModalOpen] = useState(false);
  const [streamModalHost, setStreamModalHost] = useState<Host | null>(null);
  const [streamModalDevice, setStreamModalDevice] = useState<Device | null>(null);

  // Handle overlay click to open stream modal
  const handleOverlayClick = (deviceData: any) => {
    console.log('[@HeatmapViewer] Opening stream modal for device:', deviceData);

    // Get real host and device data from HostManagerProvider
    const realHost = getHostByName(deviceData.host_name);

    if (!realHost) {
      console.error('[@HeatmapViewer] Host not found:', deviceData.host_name);
      setError(`Host "${deviceData.host_name}" not found`);
      return;
    }

    // Look for the specific device in the host's devices
    const hostDevices = getDevicesFromHost(deviceData.host_name);
    const realDevice = hostDevices.find(d => d.device_id === deviceData.device_id);

    if (!realDevice) {
      console.error('[@HeatmapViewer] Device not found:', deviceData.device_id, 'in host:', deviceData.host_name);
      setError(`Device "${deviceData.device_id}" not found in host "${deviceData.host_name}"`);
      return;
    }

    console.log('[@HeatmapViewer] Found real host:', realHost);
    console.log('[@HeatmapViewer] Found real device:', realDevice);

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
    } catch (error) {
      console.error('Error generating report:', error);
      setError('Failed to generate report');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
      {error && (
        <Box sx={{
          p: 1,
          bgcolor: 'error.main',
          color: 'error.contrastText',
          borderRadius: 1,
          mb: 1,
          fontSize: '0.8rem'
        }}>
          {error}
          <IconButton
            size="small"
            onClick={() => setError(null)}
            sx={{ ml: 1, color: 'inherit', p: 0.5 }}
          >
            ×
          </IconButton>
        </Box>
      )}

      {/* Header - Compact version for embedded view */}
      <Box sx={{ mb: 1 }}>
        <Card sx={{ bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.50' }}>
          <CardContent sx={{ py: 1, px: 2 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <HeatmapIcon color="primary" sx={{ fontSize: 18 }} />
                <Typography variant="subtitle2" fontWeight={600}>Heatmap</Typography>
                {timeline[currentIndex] && (
                  <Typography variant="caption" sx={{ ml: 1, color: 'text.primary' }}>
                    {timeline[currentIndex].isToday ? 'Today' : 'Yesterday'} {timeline[currentIndex].displayTime.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                )}
                <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                  Frame {currentIndex + 1} / {timeline.length}
                </Typography>
                {hasIncidents() && (
                  <Typography variant="caption" sx={{ ml: 1, color: 'error.main', fontWeight: 'bold' }}>
                    Incidents
                  </Typography>
                )}
              </Box>

              <Box display="flex" alignItems="center" gap={2}>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Typography variant="caption">Devices</Typography>
                  <Typography variant="caption" fontWeight="bold">
                    {analysisData?.hosts_count || 0}
                  </Typography>
                </Box>

                <FormControl size="small" sx={{ minWidth: 70 }}>
                  <Select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as 'ALL' | 'OK' | 'KO')}
                    sx={{ fontSize: '0.7rem', height: '24px' }}
                  >
                    <MenuItem value="ALL" sx={{ fontSize: '0.7rem' }}>ALL</MenuItem>
                    <MenuItem value="OK" sx={{ fontSize: '0.7rem' }}>OK</MenuItem>
                    <MenuItem value="KO" sx={{ fontSize: '0.7rem' }}>KO</MenuItem>
                  </Select>
                </FormControl>

                {/* Go to Latest Button */}
                <Tooltip title="Go to Latest">
                  <IconButton size="small" onClick={goToLatest} sx={{ p: 0.5 }}>
                    <OpenInNew sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>

                {/* Generate Report Button */}
                <Tooltip title="Generate Report">
                  <span>
                    <IconButton
                      size="small"
                      onClick={handleGenerateReport}
                      disabled={isGeneratingReport || !analysisData || !timeline[currentIndex]}
                      sx={{ p: 0.5 }}
                    >
                      <GridView sx={{ fontSize: 16 }} />
                    </IconButton>
                  </span>
                </Tooltip>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Mosaic Player - The main heatmap visualization */}
      <Box sx={{ flex: 1, minHeight: 0 }}>
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

// Main component with providers
export const HeatmapViewer: React.FC = () => {
  return (
    <HostManagerProvider>
      <DeviceDataProvider>
        <HeatmapViewerContent />
      </DeviceDataProvider>
    </HostManagerProvider>
  );
};

export default HeatmapViewer;
