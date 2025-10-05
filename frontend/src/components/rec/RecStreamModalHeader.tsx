import {
  Close as CloseIcon,
  Tv as TvIcon,
  Analytics as AnalyticsIcon,
  SmartToy as AIIcon,
  Language as WebIcon,
  VolumeOff as VolumeOffIcon,
  VolumeUp as VolumeUpIcon,
  Refresh as RefreshIcon,
  RadioButtonChecked as LiveIcon,
  History as ArchiveIcon,
  CameraAlt as CameraIcon,
} from '@mui/icons-material';
import { Box, IconButton, Typography, Button, CircularProgress, ToggleButtonGroup, ToggleButton } from '@mui/material';
import React from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { PowerButton } from '../controller/power/PowerButton';

interface RecStreamModalHeaderProps {
  host: Host;
  device?: Device;
  
  // State
  monitoringMode: boolean;
  restartMode: boolean;
  isLiveMode: boolean;
  currentQuality: 'low' | 'sd' | 'hd';
  isQualitySwitching: boolean;
  isMuted: boolean;
  isControlActive: boolean;
  isControlLoading: boolean;
  aiAgentMode: boolean;
  showWeb: boolean;
  showRemote: boolean;
  isDesktopDevice: boolean;
  hasPowerControl: boolean;

  // Handlers
  onScreenshot: () => void;
  onToggleLiveMode: () => void;
  onQualityChange: (event: React.MouseEvent<HTMLElement>, newQuality: 'low' | 'sd' | 'hd' | null) => void;
  onToggleMute: () => void;
  onToggleControl: () => void;
  onToggleMonitoring: () => void;
  onToggleRestart: () => void;
  onToggleAiAgent: () => void;
  onToggleWeb: () => void;
  onToggleRemote: () => void;
  onClose: () => void;
}

export const RecStreamModalHeader: React.FC<RecStreamModalHeaderProps> = ({
  host,
  device,
  monitoringMode,
  restartMode,
  isLiveMode,
  currentQuality,
  isQualitySwitching,
  isMuted,
  isControlActive,
  isControlLoading,
  aiAgentMode,
  showWeb,
  showRemote,
  isDesktopDevice,
  hasPowerControl,
  onScreenshot,
  onToggleLiveMode,
  onQualityChange,
  onToggleMute,
  onToggleControl,
  onToggleMonitoring,
  onToggleRestart,
  onToggleAiAgent,
  onToggleWeb,
  onToggleRemote,
  onClose,
}) => {
  return (
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
      <Typography variant="h6" component="h2">
        {device?.device_name || host.host_name} -{' '}
        {monitoringMode ? 'Monitoring' : restartMode ? 'Restart Player' : isLiveMode ? 'Live Stream' : '24h Archive'}
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {/* Screenshot Button - Only show when NOT in monitoring or restart mode */}
        {!monitoringMode && !restartMode && (
          <IconButton
            onClick={onScreenshot}
            sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
            aria-label="Take Screenshot"
            title="Take Screenshot (opens in new tab)"
          >
            <CameraIcon />
          </IconButton>
        )}

        {/* Live/Restart Mode Toggle Button Group - Only show when NOT in monitoring or restart mode */}
        {!monitoringMode && !restartMode && (
          <ToggleButtonGroup
            value={isLiveMode ? 'live' : 'restart'}
            exclusive
            onChange={(_event: React.MouseEvent<HTMLElement>, newMode: 'live' | 'restart' | null) => {
              if (newMode && newMode !== (isLiveMode ? 'live' : 'restart')) {
                onToggleLiveMode();
              }
            }}
            size="small"
            aria-label="Mode selection"
            sx={{
              '& .MuiToggleButton-root': {
                fontSize: '0.75rem',
                minWidth: 50,
                px: 1,
                border: '1px solid rgba(255, 255, 255, 0.12)',
                '&.Mui-selected': {
                  backgroundColor: isLiveMode ? 'error.main' : 'primary.main',
                  color: 'white',
                },
              },
            }}
          >
            <ToggleButton value="live" aria-label="Live mode">
              <LiveIcon sx={{ fontSize: 16, mr: 0.5 }} />
              Live
            </ToggleButton>
            <ToggleButton value="restart" aria-label="Restart mode">
              <ArchiveIcon sx={{ fontSize: 16, mr: 0.5 }} />
              Restart
            </ToggleButton>
          </ToggleButtonGroup>
        )}

        {/* Quality Toggle Button Group - Only show when NOT in monitoring or restart mode */}
        {!monitoringMode && !restartMode && (
          <ToggleButtonGroup
            value={currentQuality}
            exclusive
            onChange={onQualityChange}
            size="small"
            aria-label="Quality selection"
            sx={{
              backgroundColor: isQualitySwitching ? 'warning.main' : undefined, // Orange during transition
              '& .MuiToggleButton-root': {
                fontSize: '0.75rem',
                minWidth: 45,
                px: 1,
                border: '1px solid rgba(255, 255, 255, 0.12)',
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                },
              },
            }}
          >
            <ToggleButton
              value="low"
              aria-label="Low quality"
              title="Switch to LOW Quality (320x180) - Fastest loading"
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'success.main',
                  '&:hover': {
                    backgroundColor: 'success.dark',
                  },
                },
              }}
            >
              LOW
            </ToggleButton>
            <ToggleButton
              value="sd"
              aria-label="Standard definition"
              title="Switch to SD Quality (640x360) - Balanced"
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                },
              }}
            >
              SD
            </ToggleButton>
            <ToggleButton
              value="hd"
              aria-label="High definition"
              title="Switch to HD Quality (1280x720) - Best quality"
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'secondary.main',
                  '&:hover': {
                    backgroundColor: 'secondary.dark',
                  },
                },
              }}
            >
              HD
            </ToggleButton>
          </ToggleButtonGroup>
        )}

        {/* Volume Toggle Button - Only show when NOT in monitoring mode */}
        {!monitoringMode && !restartMode && (
          <IconButton
            onClick={onToggleMute}
            sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
            title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
          >
            {isMuted ? <VolumeOffIcon /> : <VolumeUpIcon />}
          </IconButton>
        )}

        {/* Take Control Button */}
        <Button
          variant={isControlActive ? 'contained' : 'outlined'}
          size="small"
          onClick={onToggleControl}
          disabled={isControlLoading}
          startIcon={isControlLoading ? <CircularProgress size={16} /> : <TvIcon />}
          color={isControlActive ? 'success' : 'primary'}
          sx={{
            fontSize: '0.75rem',
            minWidth: 120,
            color: isControlActive ? 'white' : 'inherit',
          }}
          title={
            isControlLoading
              ? 'Processing...'
              : isControlActive
                ? 'Release Control'
                : 'Take Control'
          }
        >
          {isControlLoading
            ? 'Processing...'
            : isControlActive
              ? 'Release Control'
              : 'Take Control'}
        </Button>

        {/* Power Control Button */}
        {hasPowerControl && device && (
          <PowerButton host={host} device={device} disabled={!isControlActive} />
        )}

        {/* Monitoring Toggle Button */}
        <Button
          variant={monitoringMode ? 'contained' : 'outlined'}
          size="small"
          onClick={onToggleMonitoring}
          disabled={!isControlActive}
          startIcon={<AnalyticsIcon />}
          color={monitoringMode ? 'warning' : 'primary'}
          sx={{
            fontSize: '0.75rem',
            minWidth: 120,
            color: monitoringMode ? 'white' : 'inherit',
          }}
          title={
            !isControlActive
              ? 'Take control first to enable monitoring'
              : monitoringMode
                ? 'Disable Monitoring'
                : 'Enable Monitoring'
          }
        >
          {monitoringMode ? 'Stop Monitoring' : 'Monitoring'}
        </Button>

        {/* Restart Toggle Button */}
        <Button
          variant={restartMode ? 'contained' : 'outlined'}
          size="small"
          onClick={onToggleRestart}
          disabled={!isControlActive}
          startIcon={<RefreshIcon />}
          color={restartMode ? 'secondary' : 'primary'}
          sx={{
            fontSize: '0.75rem',
            minWidth: 120,
            color: restartMode ? 'white' : 'inherit',
          }}
          title={
            !isControlActive
              ? 'Take control first to enable restart mode'
              : restartMode
                ? 'Disable Restart Player'
                : 'Enable Restart Player'
          }
        >
          {restartMode ? 'Stop Restart' : 'Restart'}
        </Button>

        {/* AI Agent Toggle Button */}
        <Button
          variant={aiAgentMode ? 'contained' : 'outlined'}
          size="small"
          onClick={onToggleAiAgent}
          disabled={!isControlActive}
          startIcon={<AIIcon />}
          color={aiAgentMode ? 'info' : 'primary'}
          sx={{
            fontSize: '0.75rem',
            minWidth: 120,
            color: aiAgentMode ? 'white' : 'inherit',
          }}
          title={
            !isControlActive
              ? 'Take control first to enable AI agent'
              : aiAgentMode
                ? 'Disable AI Agent'
                : 'Enable AI Agent'
          }
        >
          {aiAgentMode ? 'Stop AI Agent' : 'AI Agent'}
        </Button>

        {/* Web Panel Toggle Button */}
        {isDesktopDevice && (
          <Button
            variant={showWeb ? 'contained' : 'outlined'}
            size="small"
            onClick={onToggleWeb}
            disabled={!isControlActive}
            startIcon={<WebIcon />}
            color={showWeb ? 'secondary' : 'primary'}
            sx={{
              fontSize: '0.75rem',
              minWidth: 100,
              color: showWeb ? 'white' : 'inherit',
            }}
            title={
              !isControlActive
                ? 'Take control first to use web automation'
                : showWeb
                  ? 'Hide Web'
                  : 'Show Web '
            }
          >
            {showWeb ? 'Hide Web' : 'Show Web'}
          </Button>
        )}

        {/* Remote/Terminal Toggle Button */}
        <Button
          variant="outlined"
          size="small"
          onClick={onToggleRemote}
          disabled={!isControlActive}
          sx={{
            fontSize: '0.75rem',
            minWidth: 100,
            color: 'inherit',
          }}
          title={
            !isControlActive
              ? `Take control first to use ${isDesktopDevice ? 'terminal' : 'remote'}`
              : showRemote
                ? `Hide ${isDesktopDevice ? 'Terminal' : 'Remote'}`
                : `Show ${isDesktopDevice ? 'Terminal' : 'Remote'}`
          }
        >
          {showRemote
            ? `Hide ${isDesktopDevice ? 'Terminal' : 'Remote'}`
            : `Show ${isDesktopDevice ? 'Terminal' : 'Remote'}`}
        </Button>

        {/* Close Button */}
        <IconButton
          onClick={onClose}
          sx={{ color: 'grey.300', '&:hover': { color: 'white' } }}
          aria-label="Close"
        >
          <CloseIcon />
        </IconButton>
      </Box>
    </Box>
  );
};
