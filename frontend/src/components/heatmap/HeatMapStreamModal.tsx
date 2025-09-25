import { Close as CloseIcon } from '@mui/icons-material';
import { Modal, Box, IconButton, Typography } from '@mui/material';
import React from 'react';

import { EnhancedHLSPlayer } from '../video/EnhancedHLSPlayer';

interface DeviceInfo {
  host_name: string;
  device_id: string;
  device_name?: string;
  image_url: string;
  analysis_json: {
    audio?: boolean;
    blackscreen?: boolean;
    freeze?: boolean;
    volume_percentage?: number;
    mean_volume_db?: number;
    freeze_diffs?: number[];
    last_3_filenames?: string[];
  };
}

interface HeatMapStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  deviceInfo: DeviceInfo | null;
  timestamp?: string;
}

export const HeatMapStreamModal: React.FC<HeatMapStreamModalProps> = ({
  isOpen,
  onClose,
  deviceInfo,
  timestamp,
}) => {
  if (!isOpen || !deviceInfo) return null;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        zIndex: 1300 // Ensure it appears above other modals
      }}
    >
      <Box
        sx={{
          width: '90vw',
          height: '80vh',
          bgcolor: 'background.paper',
          borderRadius: 2,
          boxShadow: 24,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: 'grey.800',
            color: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderRadius: '8px 8px 0 0',
            minHeight: 48,
          }}
        >
          <Box>
            <Typography variant="h6" component="h2">
              {deviceInfo.device_name || `${deviceInfo.host_name}-${deviceInfo.device_id}`} - Live Stream
            </Typography>
            {timestamp && (
              <Typography variant="caption" sx={{ color: 'grey.300' }}>
                Heatmap Time: {new Date(timestamp).toLocaleString()}
              </Typography>
            )}
          </Box>

          <IconButton
            onClick={onClose}
            sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
            aria-label="Close"
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Stream Content */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'black',
            p: 2,
          }}
        >
          <EnhancedHLSPlayer
            deviceId={deviceInfo.device_id}
            hostName={deviceInfo.host_name}
            width="100%"
            height="100%"
            autoPlay={true}
          />
        </Box>

        {/* Device Info Footer */}
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: 'grey.100',
            borderTop: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Box>
            <Typography variant="body2" fontWeight="bold">
              Device: {deviceInfo.host_name}-{deviceInfo.device_id}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Click on the player to access full controls and timeline
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {deviceInfo.analysis_json.audio !== undefined && (
              <Typography 
                variant="caption" 
                color={deviceInfo.analysis_json.audio ? 'success.main' : 'error.main'}
              >
                Audio: {deviceInfo.analysis_json.audio ? 'OK' : 'NO'}
              </Typography>
            )}
            {deviceInfo.analysis_json.volume_percentage !== undefined && (
              <Typography variant="caption">
                Volume: {deviceInfo.analysis_json.volume_percentage}%
              </Typography>
            )}
            {deviceInfo.analysis_json.blackscreen && (
              <Typography variant="caption" color="error.main">
                Blackscreen Detected
              </Typography>
            )}
            {deviceInfo.analysis_json.freeze && (
              <Typography variant="caption" color="error.main">
                Freeze Detected ({(deviceInfo.analysis_json.freeze_diffs || []).length} diffs)
              </Typography>
            )}
          </Box>
        </Box>
      </Box>
    </Modal>
  );
};
