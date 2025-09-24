import {
  GridView as HeatmapIcon,
  OpenInNew,
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
import { useHeatmapTimeline } from '../hooks/useHeatmapTimeline';

const Heatmap: React.FC = () => {
  const {
    timeline,
    currentIndex,
    setCurrentIndex,
    currentItem,
    analysisData,
    analysisLoading,
    hasIncidents,
    goToLatest
  } = useHeatmapTimeline();

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  
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

  return (
    <Box>
      {error && (
        <MuiAlert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </MuiAlert>
      )}

      {/* Header */}
      <Box sx={{ mb: 0.5 }}>
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
                    {hasIncidents() ? 'Incidents Detected' : 'All Good'}
                  </Typography>
                </Box>

                {/* Go to Latest Button */}
                <Tooltip title="Go to Latest">
                  <IconButton size="small" onClick={goToLatest}>
                    <OpenInNew />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Mosaic Player */}
      <MosaicPlayer
        timeline={timeline}
        currentIndex={currentIndex}
        onIndexChange={setCurrentIndex}
        onCellClick={handleCellClick}
        hasIncidents={hasIncidents()}
        isLoading={analysisLoading}
      />

      {/* Analysis Section */}
      <HeatMapAnalysisSection
        images={analysisData?.devices || []}
        analysisExpanded={analysisExpanded}
        onToggleExpanded={() => setAnalysisExpanded(!analysisExpanded)}
      />

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