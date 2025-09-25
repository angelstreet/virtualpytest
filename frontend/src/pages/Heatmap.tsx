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
import { HeatMapStreamModal } from '../components/heatmap/HeatMapStreamModal';
import { HeatMapHistory } from '../components/heatmap/HeatMapHistory';
import { MosaicPlayer } from '../components/MosaicPlayer';
import { useHeatmap } from '../hooks/useHeatmap';

const Heatmap: React.FC = () => {
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

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  
  // Freeze modal state
  const [freezeModalOpen, setFreezeModalOpen] = useState(false);
  const [freezeModalImage, setFreezeModalImage] = useState<any>(null);
  
  // Stream modal state
  const [streamModalOpen, setStreamModalOpen] = useState(false);
  const [streamModalDevice, setStreamModalDevice] = useState<any>(null);

  // Handle freeze click from analysis table
  const handleFreezeClick = (deviceData: any) => {
    if (deviceData?.analysis_json?.freeze) {
      setFreezeModalImage(deviceData);
      setFreezeModalOpen(true);
    }
  };

  // Handle overlay click to open stream modal
  const handleOverlayClick = (deviceData: any) => {
    setStreamModalDevice(deviceData);
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
      <Box>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <HeatmapIcon color="primary" />
                <Typography variant="h6">24h Heatmap</Typography>
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
      <HeatMapStreamModal
        isOpen={streamModalOpen}
        onClose={() => setStreamModalOpen(false)}
        deviceInfo={streamModalDevice}
        timestamp={analysisData?.timestamp}
      />
    </Box>
  );
};

export default Heatmap;