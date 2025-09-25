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
    hasDataError,
    generateReport,
    getMosaicUrl,
    getFilteredDevices
  } = useHeatmap();

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OK' | 'KO'>('ALL');
  
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
          filter={filter}
          getMosaicUrl={getMosaicUrl}
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
          images={getFilteredDevices(analysisData?.devices || [], filter)}
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