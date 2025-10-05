import { Close as CloseIcon } from '@mui/icons-material';
import { Modal, Box, IconButton, Typography } from '@mui/material';
import React from 'react';

// Import the device type from AnalysisData
type HeatmapImage = {
  host_name: string;
  device_id: string;
  image_url: string;
  analysis_json: {
    audio?: boolean;
    blackscreen?: boolean;
    freeze?: boolean;
    volume_percentage?: number;
    mean_volume_db?: number;
    freeze_diffs?: number[];
    last_3_thumbnails?: string[];  // R2 thumbnail URLs
  };
};

interface HeatMapFreezeModalProps {
  freezeModalOpen: boolean;
  freezeModalImage: HeatmapImage | null;
  onClose: () => void;
  constructFrameUrl: (filename: string, baseUrl: string) => string;
  timestamp?: string; // Add timestamp for metadata display
}

export const HeatMapFreezeModal: React.FC<HeatMapFreezeModalProps> = ({
  freezeModalOpen,
  freezeModalImage,
  onClose,
  constructFrameUrl,
  timestamp,
}) => {
  if (!freezeModalOpen || !freezeModalImage) return null;

  // Use existing MonitoringAnalysis fields instead of freeze_details
  const analysisJson = freezeModalImage.analysis_json;
  if (!analysisJson || !analysisJson.freeze) return null;

  const thumbnailUrls = analysisJson.last_3_thumbnails || [];
  const frameDifferences = analysisJson.freeze_diffs || [];

  // Only show modal if we have thumbnail URLs
  if (thumbnailUrls.length === 0) return null;

  // Debug: Log the thumbnail URLs being displayed
  console.log('[@HeatMapFreezeModal] Displaying freeze thumbnails:', {
    device: `${freezeModalImage.host_name}-${freezeModalImage.device_id}`,
    thumbnailCount: thumbnailUrls.length,
    thumbnails: thumbnailUrls,
    diffs: frameDifferences
  });

  return (
    <Modal
      open={freezeModalOpen}
      onClose={onClose}
      sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <Box
        sx={{
          width: '90vw',
          height: '70vh',
          bgcolor: 'black',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header with close button */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'flex-end',
            p: 0.25,
            minHeight: '24px',
            bgcolor: 'rgba(0,0,0,0.8)',
          }}
        >
          <IconButton
            onClick={onClose}
            size="small"
            sx={{
              color: 'white',
              padding: '2px',
              minWidth: '20px',
              minHeight: '20px',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' },
              '& .MuiSvgIcon-root': {
                fontSize: '16px',
              },
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Title and Timestamp Metadata */}
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            p: 1,
            bgcolor: 'rgba(0,0,0,0.8)',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Typography
            variant="h6"
            sx={{
              color: 'white',
              fontWeight: 'bold',
              mb: 0.5,
            }}
          >
            Capture
          </Typography>
          {timestamp && (
            <Typography
              variant="body2"
              sx={{
                color: 'rgba(255,255,255,0.8)',
                fontSize: '0.875rem',
              }}
            >
              {new Date(timestamp).toLocaleString()}
            </Typography>
          )}
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255,255,255,0.6)',
              fontSize: '0.75rem',
              mt: 0.5,
            }}
          >
            Device: {freezeModalImage.host_name}-{freezeModalImage.device_id}
          </Typography>
        </Box>

        {/* 3 Images side by side */}
        <Box sx={{ display: 'flex', flex: 1, gap: 1, p: 1 }}>
          {thumbnailUrls.map((thumbnailUrl: string, index: number) => {
            // Thumbnails are now always R2 URLs (https://...r2.../alerts/freeze/.../thumb_0.jpg)
            // No need for format detection or URL construction - use directly
            const isR2Url = thumbnailUrl.startsWith('http://') || thumbnailUrl.startsWith('https://');
            
            // Extract just the filename for sequence number display
            const cleanFilename = thumbnailUrl.includes('/')
              ? thumbnailUrl.split('/').pop() || thumbnailUrl
              : thumbnailUrl;
            
            // Use R2 URL directly, or fallback to constructFrameUrl for legacy local paths
            const frameUrl = isR2Url 
              ? thumbnailUrl 
              : constructFrameUrl(cleanFilename, freezeModalImage.image_url);
            
            const diff = frameDifferences[index];

            // Extract sequence number from filename (format: capture_0001.jpg or thumb_0.jpg)
            const sequenceMatch = cleanFilename.match(/(?:capture_|thumb_)(\d+)/);
            const sequenceNumber = sequenceMatch ? sequenceMatch[1] : '';

            // Format sequence number for display
            const formatSequence = (seq: string) => {
              if (!seq) return 'Unknown';
              return `#${seq.padStart(4, '0')}`;
            };

            return (
              <Box
                key={thumbnailUrl}
                sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    color: 'white',
                    textAlign: 'center',
                    p: 0.5,
                    bgcolor: 'rgba(0,0,0,0.7)',
                    fontSize: '0.75rem',
                  }}
                >
                  {sequenceNumber ? formatSequence(sequenceNumber) : `Frame ${index + 1}`} - Frame ({diff})
                </Typography>
                <img
                  src={frameUrl}
                  alt={`Frame ${index}`}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain', // Keep original size and aspect ratio
                  }}
                />
              </Box>
            );
          })}
        </Box>
      </Box>
    </Modal>
  );
};
