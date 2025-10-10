import { Box, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { LiveMonitoringEvent } from '../../types/pages/Monitoring_Types';

interface ActionHistoryProps {
  lastAction?: string;
  lastActionTimestamp?: number;
  actionParams?: Record<string, any>;
  liveEvents?: LiveMonitoringEvent[];
}

interface ActionEntry {
  command: string;
  timestamp: number;
  params?: Record<string, any>;
  id: string;
}

export const ActionHistory: React.FC<ActionHistoryProps> = ({
  lastAction,
  lastActionTimestamp,
  actionParams,
  liveEvents = [],
}) => {
  const [actions, setActions] = useState<ActionEntry[]>([]);

  // Add zapping events from live events feed
  useEffect(() => {
    if (!liveEvents || liveEvents.length === 0) return;
    
    // Convert zapping events to action entries
    const zappingActions = liveEvents
      .filter(event => event.event_type === 'zapping')
      .map(event => ({
        command: event.detection_type === 'automatic'
          ? `📺 ZAP → ${event.channel_name} ${event.channel_number ? `(${event.channel_number})` : ''}`
          : `📺 MANUAL ZAP → ${event.channel_name} ${event.channel_number ? `(${event.channel_number})` : ''}`,
        timestamp: new Date(event.timestamp).getTime() / 1000,
        params: {
          channel_name: event.channel_name,
          channel_number: event.channel_number,
          program_name: event.program_name,
          detection_type: event.detection_type,
        },
        id: event.event_id,
      }));
    
    // Merge with existing actions
    setActions(prev => {
      const combined = [...zappingActions, ...prev];
      const uniqueMap = new Map(combined.map(a => [a.id, a]));
      const unique = Array.from(uniqueMap.values());
      return unique
        .sort((a, b) => b.timestamp - a.timestamp)
        .slice(0, 3); // Keep last 3 actions
    });
  }, [liveEvents]);

  // Add new action when it changes
  useEffect(() => {
    if (!lastAction || !lastActionTimestamp) return;

    const newAction: ActionEntry = {
      command: lastAction,
      timestamp: lastActionTimestamp,
      params: actionParams,
      id: `${lastActionTimestamp}-${lastAction}`,
    };

    setActions(prev => {
      // Check if this action is already in the list (avoid duplicates)
      if (prev.some(a => a.id === newAction.id)) return prev;

      // Add new action at the top, keep only last 3
      return [newAction, ...prev].slice(0, 3);
    });
  }, [lastAction, lastActionTimestamp, actionParams]);

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

