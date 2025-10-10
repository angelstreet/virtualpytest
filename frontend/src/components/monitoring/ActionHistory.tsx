import { Box, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { MonitoringAnalysis } from '../../types/pages/Monitoring_Types';

interface ActionHistoryProps {
  monitoringAnalysis?: MonitoringAnalysis | null;
}

interface ActionEntry {
  command: string;
  timestamp: number;
  params?: Record<string, any>;
  id: string;
}

export const ActionHistory: React.FC<ActionHistoryProps> = ({
  monitoringAnalysis,
}) => {
  const [actions, setActions] = useState<ActionEntry[]>([]);

  // ✅ Process monitoring analysis - includes both regular actions AND zapping detection from frame JSON
  useEffect(() => {
    if (!monitoringAnalysis) return;

    const currentActions: ActionEntry[] = [];

    // Check for zapping detection in frame JSON
    if (monitoringAnalysis.zapping_detected) {
      const zappingAction: ActionEntry = {
        command: monitoringAnalysis.zapping_detection_type === 'automatic'
          ? `📺 ZAP → ${monitoringAnalysis.zapping_channel_name || 'Unknown'} ${monitoringAnalysis.zapping_channel_number ? `(${monitoringAnalysis.zapping_channel_number})` : ''}`
          : `📺 MANUAL ZAP → ${monitoringAnalysis.zapping_channel_name || 'Unknown'} ${monitoringAnalysis.zapping_channel_number ? `(${monitoringAnalysis.zapping_channel_number})` : ''}`,
        timestamp: monitoringAnalysis.zapping_detected_at 
          ? new Date(monitoringAnalysis.zapping_detected_at).getTime() / 1000
          : Date.now() / 1000,
        params: {
          channel_name: monitoringAnalysis.zapping_channel_name,
          channel_number: monitoringAnalysis.zapping_channel_number,
          program_name: monitoringAnalysis.zapping_program_name,
          detection_type: monitoringAnalysis.zapping_detection_type,
        },
        id: `zap-${monitoringAnalysis.zapping_detected_at || Date.now()}`,
      };
      currentActions.push(zappingAction);
    }

    // Check for regular action in frame JSON
    if (monitoringAnalysis.last_action_executed && monitoringAnalysis.last_action_timestamp) {
      const regularAction: ActionEntry = {
        command: monitoringAnalysis.last_action_executed,
        timestamp: monitoringAnalysis.last_action_timestamp,
        params: monitoringAnalysis.action_params,
        id: `${monitoringAnalysis.last_action_timestamp}-${monitoringAnalysis.last_action_executed}`,
      };
      currentActions.push(regularAction);
    }

    // Merge with existing actions, keep unique, sort by timestamp, keep last 3
    if (currentActions.length > 0) {
      setActions(prev => {
        const combined = [...currentActions, ...prev];
        const uniqueMap = new Map(combined.map(a => [a.id, a]));
        const unique = Array.from(uniqueMap.values());
        return unique
          .sort((a, b) => b.timestamp - a.timestamp)
          .slice(0, 3);
      });
    }
  }, [monitoringAnalysis]);

  // Auto-remove actions after 10 seconds (increased for zapping events)
  useEffect(() => {
    const now = Date.now() / 1000;
    const timers = actions.map(action => {
      const age = now - action.timestamp;
      const remainingTime = Math.max(0, 10 - age) * 1000;

      return setTimeout(() => {
        setActions(prev => prev.filter(a => a.id !== action.id));
      }, remainingTime);
    });

    return () => timers.forEach(clearTimeout);
  }, [actions]);

  if (actions.length === 0) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        zIndex: 30,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        pointerEvents: 'none',
      }}
    >
      {actions.map((action, index) => {
        const isZapping = action.command.includes('ZAP');
        const isManual = action.command.includes('MANUAL');
        
        return (
          <Box
            key={action.id}
            sx={{
              p: index === 0 ? 1.5 : 1,
              borderRadius: 1,
              backgroundColor: isZapping
                ? isManual
                  ? 'rgba(255, 165, 0, 0.9)'  // Orange for manual zapping
                  : 'rgba(0, 255, 0, 0.9)'    // Green for automatic zapping
                : 'rgba(0, 191, 255, 0.8)',   // Blue for regular actions
              minWidth: index === 0 ? 150 : 120,
              transition: 'all 0.3s ease',
              opacity: index === 0 ? 1 : 0.7,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: '#ffffff',
                fontWeight: index === 0 ? 'bold' : 'normal',
                fontSize: index === 0 ? '0.85rem' : '0.75rem',
              }}
            >
              {action.command}
            </Typography>
            
            {/* Show program name for zapping events */}
            {isZapping && action.params?.program_name && (
              <Typography
                variant="caption"
                sx={{
                  color: '#ffffff',
                  display: 'block',
                  fontSize: index === 0 ? '0.75rem' : '0.7rem',
                  fontStyle: 'italic',
                }}
              >
                {action.params.program_name}
              </Typography>
            )}
            
            {/* Show key for regular actions */}
            {!isZapping && action.params?.key && (
              <Typography
                variant="caption"
                sx={{
                  color: '#ffffff',
                  display: 'block',
                  fontSize: index === 0 ? '0.75rem' : '0.7rem',
                }}
              >
                Key: {action.params.key}
              </Typography>
            )}
            
            <Typography
              variant="caption"
              sx={{
                color: '#cccccc',
                display: 'block',
                fontSize: index === 0 ? '0.7rem' : '0.65rem',
              }}
            >
              {new Date(action.timestamp * 1000).toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
};

