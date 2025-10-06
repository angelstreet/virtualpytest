import { Close as CloseIcon } from '@mui/icons-material';
import { Modal, Box, IconButton, Typography } from '@mui/material';
import React from 'react';

interface HeatMapFreezeModalProps {
  freezeModalOpen: boolean;
  hostName: string;
  deviceId: string;
  thumbnailUrls: string[]; // Direct R2 URLs (3 images)
  freezeDiffs: number[]; // Frame differences (3 values)
  timestamp?: string;
  onClose: () => void;
}

export const HeatMapFreezeModal: React.FC<HeatMapFreezeModalProps> = ({
  freezeModalOpen,
  hostName,
  deviceId,
  thumbnailUrls,
  freezeDiffs,
  timestamp,
  onClose,
}) => {
  if (!freezeModalOpen || thumbnailUrls.length === 0) return null;

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
            Device: {hostName}-{deviceId}
          </Typography>
        </Box>

        {/* 3 Images side by side */}
        <Box sx={{ display: 'flex', flex: 1, gap: 1, p: 1 }}>
          {thumbnailUrls.map((imageUrl: string, index: number) => {
            const diff = freezeDiffs[index];
            const frameLabels = ['Frame -2', 'Frame -1', 'Current'];

            return (
              <Box
                key={index}
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
                  {frameLabels[index]} - Diff ({diff !== undefined ? diff.toFixed(1) : 'N/A'})
                </Typography>
                <img
                  src={imageUrl}
                  alt={`Frame ${index}`}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
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
