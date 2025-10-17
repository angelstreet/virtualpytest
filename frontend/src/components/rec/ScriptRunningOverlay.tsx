/**
 * Script Running Overlay Component
 * 
 * Displays real-time script execution progress by polling running.log from hot storage.
 * Minimal design inspired by ActionHistory.tsx with styling consistency from AIStepDisplay.tsx
 * 
 * Features:
 * - Shows previous/current/next steps
 * - Current step expandable to show actions/verifications
 * - Start time and estimated end time
 * - Show/hide toggle button
 * - Auto-polls every 2 seconds
 */

import React, { useState, useEffect } from 'react';
import { Box, Typography, IconButton, CircularProgress } from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Lock as LockIcon,
} from '@mui/icons-material';

import { Host } from '../../types/common/Host_Types';
import { buildRunningLogUrl } from '../../utils/buildUrlUtils';

interface ScriptRunningOverlayProps {
  host: Host;
  device_id: string;
}

interface StepInfo {
  step_number: number;
  command: string;
  description?: string;
  params?: any;
  status?: 'pending' | 'current' | 'completed' | 'failed';
}

interface ActionInfo {
  command: string;
  params?: any;
  status?: 'pending' | 'current' | 'completed' | 'failed';
}

interface VerificationInfo {
  command: string;
  verification_type: string;
  status?: 'pending' | 'current' | 'completed' | 'failed';
}

interface RunningLogData {
  previous_step?: StepInfo;
  current_step?: StepInfo & {
    actions?: ActionInfo[];
    verifications?: VerificationInfo[];
    current_action_index?: number;
    current_verification_index?: number;
  };
  next_step?: StepInfo;
  start_time: string; // ISO timestamp
  estimated_end?: string; // ISO timestamp
  script_name: string;
  total_steps: number;
  current_step_number: number;
}

export const ScriptRunningOverlay: React.FC<ScriptRunningOverlayProps> = ({
  host,
  device_id,
}) => {
  const [logData, setLogData] = useState<RunningLogData | null>(null);
  const [isExpanded, setIsExpanded] = useState(false); // Current step expansion
  const [isCollapsed, setIsCollapsed] = useState(false); // Collapse entire overlay

  // Poll running.log every 2 seconds
  useEffect(() => {
    const fetchLog = async () => {
      try {
        // Fetch from nginx served hot storage using proper URL building utility
        // This handles HTTPS, multi-device paths, and host configuration properly
        const url = `${buildRunningLogUrl(host, device_id)}?t=${Date.now()}`;
        const response = await fetch(url);
        
        if (response.ok) {
          const data = await response.json();
          console.log('[@ScriptRunningOverlay] Raw JSON data:', data);
          setLogData(data);
        } else {
          // Log file might not exist yet or script finished
          setLogData(null);
        }
      } catch (error) {
        console.debug('[@ScriptRunningOverlay] Failed to fetch running.log:', error);
        setLogData(null);
      }
    };

    // Initial fetch
    fetchLog();

    // Poll every 2 seconds
    const interval = setInterval(fetchLog, 2000);

    return () => clearInterval(interval);
  }, [host, device_id]);

  // Don't render if no data
  if (!logData) {
    return null;
  }

  // Calculate time remaining
  const getTimeRemaining = () => {
    if (!logData.estimated_end) return null;
    const now = new Date().getTime();
    const end = new Date(logData.estimated_end).getTime();
    const remainingMs = end - now;
    if (remainingMs <= 0) return 'finishing...';
    
    const minutes = Math.floor(remainingMs / 60000);
    const seconds = Math.floor((remainingMs % 60000) / 1000);
    return minutes > 0 ? `${minutes}m ${seconds}s left` : `${seconds}s left`;
  };

  // Simple script info banner at top-left (minimal)
  const scriptInfoBanner = (
    <Box
      sx={{
        position: 'absolute',
        top: 8,
        left: 8,
        zIndex: 25,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        borderRadius: 1,
        px: 1.5,
        py: 0.75,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        pointerEvents: 'none',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <LockIcon sx={{ fontSize: '0.85rem', color: 'warning.main' }} />
        <Typography variant="caption" sx={{ color: '#fff', fontWeight: 'bold', fontSize: '0.75rem' }}>
          {logData.script_name}
        </Typography>
      </Box>
      <Typography variant="caption" sx={{ color: '#aaa', fontSize: '0.7rem' }}>
        Started: {new Date(logData.start_time).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
      </Typography>
      {logData.estimated_end && (
        <Typography variant="caption" sx={{ color: '#aaa', fontSize: '0.7rem' }}>
          Est. End: {new Date(logData.estimated_end).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
          {getTimeRemaining() && ` (${getTimeRemaining()})`}
        </Typography>
      )}
    </Box>
  );

  // Collapsed mini view at bottom-left
  if (isCollapsed) {
    return (
      <>
        {scriptInfoBanner}
        <Box
          sx={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            zIndex: 30,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            borderRadius: 1,
            p: 1,
            minWidth: 200,
            cursor: 'pointer',
          }}
          onClick={() => setIsCollapsed(false)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LockIcon sx={{ fontSize: '1rem', color: 'warning.main' }} />
            <Typography variant="caption" sx={{ color: '#fff', fontWeight: 'bold', flex: 1 }}>
              Step {logData.current_step_number}/{logData.total_steps}
            </Typography>
            {getTimeRemaining() && (
              <Typography variant="caption" sx={{ color: '#aaa', fontSize: '0.7rem' }}>
                {getTimeRemaining()}
              </Typography>
            )}
            <ExpandMoreIcon sx={{ fontSize: '1rem', color: '#aaa' }} />
          </Box>
        </Box>
      </>
    );
  }

  // Full overlay view at bottom-left
  return (
    <>
      {scriptInfoBanner}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 30,
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          borderRadius: 1,
          p: 1.5,
          minWidth: 320,
          maxWidth: 400,
          pointerEvents: 'auto',
        }}
      >
      {/* Header - minimized since script name/time shown in top banner */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', mb: 1, pb: 0.5, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <IconButton
          size="small"
          onClick={() => setIsCollapsed(true)}
          sx={{ color: '#aaa', p: 0.25 }}
          title="Minimize"
        >
          <ExpandLessIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Previous Step (faded green) */}
      {logData.previous_step && (
        <Box
          sx={{
            mb: 1,
            p: 0.75,
            backgroundColor: 'rgba(76,175,80,0.15)',
            borderRadius: 0.5,
            border: '1px solid rgba(76,175,80,0.3)',
            opacity: 0.7,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#4caf50' }} />
            <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.75rem', fontWeight: 'bold' }}>
              {logData.previous_step.step_number}. {logData.previous_step.description || logData.previous_step.command}
            </Typography>
          </Box>
        </Box>
      )}

      {/* Current Step (bright blue, expandable) */}
      {logData.current_step && (
        <Box
          sx={{
            mb: 1,
            p: 0.75,
            backgroundColor: 'rgba(33,150,243,0.2)',
            borderRadius: 0.5,
            border: '1px solid rgba(33,150,243,0.5)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CircularProgress size={12} sx={{ color: '#2196f3' }} />
            <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', flex: 1 }}>
              {logData.current_step.step_number}. {logData.current_step.description || logData.current_step.command}
            </Typography>
            {(logData.current_step.actions || logData.current_step.verifications) && (
              <IconButton
                size="small"
                onClick={() => setIsExpanded(!isExpanded)}
                sx={{ color: '#aaa', p: 0.25 }}
              >
                {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>

          {/* Expanded current step details */}
          {isExpanded && (
            <Box sx={{ ml: 1.5, mt: 0.75, borderLeft: '2px solid #444', pl: 0.75 }}>
              {/* Actions */}
              {logData.current_step.actions && logData.current_step.actions.length > 0 && (
                <Box sx={{ mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 'bold', fontSize: '0.7rem' }}>
                    Actions ({logData.current_step.current_action_index || 0}/{logData.current_step.actions.length})
                  </Typography>
                  {logData.current_step.actions.map((action, idx) => {
                    const isCurrent = idx === (logData.current_step?.current_action_index || 0) - 1;
                    const isCompleted = idx < (logData.current_step?.current_action_index || 0) - 1;
                    return (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 0.75, mt: 0.25 }}>
                        {isCurrent ? (
                          <CircularProgress size={8} sx={{ color: '#2196f3' }} />
                        ) : isCompleted ? (
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#4caf50' }} />
                        ) : (
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#666' }} />
                        )}
                        <Typography
                          variant="caption"
                          sx={{
                            color: isCurrent ? '#fff' : isCompleted ? '#4caf50' : '#aaa',
                            fontFamily: 'monospace',
                            fontSize: '0.65rem',
                          }}
                        >
                          {action.command}
                          {action.params && `(${Object.values(action.params)[0]})`}
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              )}

              {/* Verifications */}
              {logData.current_step.verifications && logData.current_step.verifications.length > 0 && (
                <Box>
                  <Typography variant="caption" sx={{ color: '#888', fontSize: '0.65rem' }}>
                    Verifications ({logData.current_step.current_verification_index || 0}/{logData.current_step.verifications.length})
                  </Typography>
                  {logData.current_step.verifications.map((verification, idx) => {
                    const isCurrent = idx === (logData.current_step?.current_verification_index || 0) - 1;
                    const isCompleted = idx < (logData.current_step?.current_verification_index || 0) - 1;
                    return (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 0.75, mt: 0.25 }}>
                        {isCurrent ? (
                          <CircularProgress size={8} sx={{ color: '#2196f3' }} />
                        ) : isCompleted ? (
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#4caf50' }} />
                        ) : (
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#666' }} />
                        )}
                        <Typography
                          variant="caption"
                          sx={{
                            color: isCurrent ? '#fff' : isCompleted ? '#4caf50' : '#888',
                            fontFamily: 'monospace',
                            fontSize: '0.6rem',
                          }}
                        >
                          {verification.command} ({verification.verification_type})
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </Box>
          )}
        </Box>
      )}

      {/* Next Step (dim gray) */}
      {logData.next_step && (
        <Box
          sx={{
            mb: 1,
            p: 0.75,
            backgroundColor: 'rgba(158,158,158,0.1)',
            borderRadius: 0.5,
            border: '1px solid rgba(158,158,158,0.2)',
            opacity: 0.6,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#666', border: '1px solid #888' }} />
            <Typography variant="caption" sx={{ color: '#aaa', fontSize: '0.75rem' }}>
              {logData.next_step.step_number}. {logData.next_step.description || logData.next_step.command}
            </Typography>
          </Box>
        </Box>
      )}

    </Box>
    </>
  );
};

