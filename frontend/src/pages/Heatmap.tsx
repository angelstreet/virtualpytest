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
    refreshCurrentData,
    hasDataError
  } = useHeatmap();

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  
  // Freeze modal state
  const [freezeModalOpen, setFreezeModalOpen] = useState(false);
  const [freezeModalImage, setFreezeModalImage] = useState<any>(null);

  // Handle device cell click for freeze analysis
  const handleCellClick = (deviceData: any) => {
    if (deviceData?.analysis_json?.freeze) {
      setFreezeModalImage(deviceData);
      setFreezeModalOpen(true);
    }
  };

  // Helper function to construct frame URLs
  const constructFrameUrl = (filename: string, originalImageUrl: string): string => {
    const cleanFilename = filename.includes('/') ? filename.split('/').pop() || filename : filename;
    const lastSlashIndex = originalImageUrl.lastIndexOf('/');
    if (lastSlashIndex === -1) return cleanFilename;
    const baseUrl = originalImageUrl.substring(0, lastSlashIndex + 1);
    return `${baseUrl}${cleanFilename}`;
  };

  // Generate report for current frame
  const handleGenerateReport = async () => {
    if (!timeline[currentIndex] || !analysisData || isGeneratingReport) return;
    
    setIsGeneratingReport(true);
    try {
      const currentItem = timeline[currentIndex];
      const reportData = {
        timeframe: 'single_frame',
        timestamp: currentItem.displayTime.toISOString(),
        time_key: currentItem.timeKey,
        mosaic_url: currentItem.mosaicUrl,
        analysis_data: analysisData,
        devices_count: analysisData.devices.length,
        incidents_count: analysisData.incidents_count
      };

      // For now, just download the data as JSON (we can enhance this later)
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `heatmap_report_${currentItem.timeKey}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      console.log('Report generated for frame:', currentItem.timeKey);
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
          <CardContent sx={{ py: 0.25, px: 1 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={0.5}>
                <HeatmapIcon color="primary" fontSize="small" />
                <Typography variant="subtitle1" fontWeight="bold">24h Heatmap</Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={2}>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Typography variant="caption">Devices</Typography>
                  <Typography variant="caption" fontWeight="bold">
                    {analysisData?.hosts_count || 0}
                  </Typography>
                </Box>
                
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Typography variant="caption">Status</Typography>
                  <Typography variant="caption" fontWeight="bold" color={hasIncidents() ? 'error' : 'success'}>
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
                <Tooltip title={
                  !timeline[currentIndex] ? "No timeline data available" :
                  !analysisData ? "No analysis data available - check if heatmap processor is running" :
                  !analysisData.devices ? "Analysis data missing devices array" :
                  isGeneratingReport ? "Generating report..." :
                  "Generate Report for Current Frame"
                }>
                  <IconButton 
                    size="small" 
                    onClick={handleGenerateReport}
                    disabled={isGeneratingReport || !analysisData || !analysisData.devices || !timeline[currentIndex]}
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
          onCellClick={handleCellClick}
          hasIncidents={hasIncidents()}
          isLoading={analysisLoading}
          hasDataError={hasDataError}
          analysisData={analysisData}
        />
      </Box>

      {/* Analysis Section */}
      <Box sx={{ mb: 3 }}>
        {/* Debug info */}
        {process.env.NODE_ENV === 'development' && (
          <Box sx={{ mb: 1, p: 1, bgcolor: 'grey.100', fontSize: '0.75rem' }}>
            <Typography variant="caption">
              Debug: analysisData={analysisData ? 'exists' : 'null'}, 
              devices={analysisData?.devices?.length || 0}, 
              hasDevicesArray={Array.isArray(analysisData?.devices)}
            </Typography>
          </Box>
        )}
        <HeatMapAnalysisSection
          images={analysisData?.devices || []}
          analysisExpanded={analysisExpanded}
          onToggleExpanded={() => setAnalysisExpanded(!analysisExpanded)}
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
      />
    </Box>
  );
};

export default Heatmap;