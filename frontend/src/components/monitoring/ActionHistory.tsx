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
  const [shownZappingIds, setShownZappingIds] = useState<Set<string>>(new Set());

  // ✅ Process monitoring analysis - includes both regular actions AND zapping detection from frame JSON
  useEffect(() => {
    if (!monitoringAnalysis) return;

    const currentActions: ActionEntry[] = [];

    // ✅ NEW: Check for zapping detection (prioritize cache for real-time, fallback to truth for historical)
    // Priority: zap_cache (real-time notification) > zap (historical truth)
    const zapData = monitoringAnalysis.zap_cache?.detected 
      ? monitoringAnalysis.zap_cache 
      : monitoringAnalysis.zap?.detected 
        ? monitoringAnalysis.zap
        : null;
    
    // DEBUG: Log zap detection
    if (monitoringAnalysis.zap_cache) {
      console.log('[ActionHistory] zap_cache found:', monitoringAnalysis.zap_cache);
    }
    if (monitoringAnalysis.zap) {
      console.log('[ActionHistory] zap found:', monitoringAnalysis.zap);
    }
    
    if (zapData) {
      const zapId = zapData.id;
      
      console.log('[ActionHistory] Zap detected! ID:', zapId, 'Already shown:', shownZappingIds.has(zapId));
      
      // ✅ CRITICAL: Only show each zapping event once (prevents duplicates from multiple frames with same zap_cache)
      if (!shownZappingIds.has(zapId)) {
        console.log('[ActionHistory] Adding zap to actions:', zapId);
        const channelName = zapData.channel_name || 'Unknown';
        const channelNumber = zapData.channel_number || '';
        const detectionType = zapData.detection_type || 'manual';
        const isCache = monitoringAnalysis.zap_cache?.detected || false;
        
        const zappingAction: ActionEntry = {
          command: detectionType === 'automatic'
            ? `📺 ZAP${isCache ? ' 🔔' : ''} → ${channelName} ${channelNumber ? `(${channelNumber})` : ''}`
            : `📺 MANUAL ZAP${isCache ? ' 🔔' : ''} → ${channelName} ${channelNumber ? `(${channelNumber})` : ''}`,
          timestamp: zapData.detected_at 
            ? new Date(zapData.detected_at).getTime() / 1000
            : Date.now() / 1000,
          params: {
            channel_name: zapData.channel_name,
            channel_number: zapData.channel_number,
            program_name: zapData.program_name,
            program_start_time: zapData.program_start_time,
            program_end_time: zapData.program_end_time,
            blackscreen_duration_ms: zapData.blackscreen_duration_ms,
            audio_silence_duration: zapData.audio_silence_duration,
            time_since_action_ms: zapData.time_since_action_ms,        // ✅ From backend
            total_zap_duration_ms: zapData.total_zap_duration_ms,      // ✅ Backend calculated
            detection_type: detectionType,
            is_cache: isCache,
            original_frame: monitoringAnalysis.zap_cache?.original_frame,
          },
          id: zapId,
        };
        currentActions.push(zappingAction);
        
        // Mark as shown immediately (synchronously update tracking)
        setShownZappingIds(prev => new Set(prev).add(zapId));
      } else {
        console.log('[ActionHistory] Zap already shown, skipping:', zapId);
      }
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

    // Merge with existing actions - CRITICAL: Only keep ONE zap at a time (newest replaces old)
    if (currentActions.length > 0) {
      console.log('[ActionHistory] Updating actions with:', currentActions);
      setActions(prev => {
        const hasNewZap = currentActions.some(a => a.command.includes('ZAP'));
        
        // If new action is a zap, remove ALL previous zaps first
        const filteredPrev = hasNewZap 
          ? prev.filter(a => !a.command.includes('ZAP'))
          : prev;
        
        const combined = [...currentActions, ...filteredPrev];
        const uniqueMap = new Map(combined.map(a => [a.id, a]));
        const unique = Array.from(uniqueMap.values());
        const sorted = unique
          .sort((a, b) => b.timestamp - a.timestamp)
          .slice(0, 3);
        console.log('[ActionHistory] Final actions to display:', sorted);
        return sorted;
      });
    }
  }, [monitoringAnalysis, shownZappingIds]);

  // Auto-remove actions after 15 seconds (zapping events need more time to read)
  useEffect(() => {
    const now = Date.now() / 1000;
    const timers = actions.map(action => {
      const age = now - action.timestamp;
      const remainingTime = Math.max(0, 15 - age) * 1000;

      return setTimeout(() => {
        setActions(prev => prev.filter(a => a.id !== action.id));
      }, remainingTime);
    });

    return () => timers.forEach(clearTimeout);
  }, [actions]);

  console.log('[ActionHistory] Rendering with actions:', actions.length, actions);
  
  if (actions.length === 0) {
    console.log('[ActionHistory] No actions to display, returning null');
    return null;
  }

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
                  : 'rgba(147, 51, 234, 0.9)' // Purple for automatic zapping
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
            
            {/* Show detailed info for zapping events - CLEAN 2-LINE FORMAT */}
            {isZapping && (
              <>
                {/* Program name (italic, white) */}
                {action.params?.program_name && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#ffffff',
                      display: 'block',
                      fontSize: index === 0 ? '0.72rem' : '0.68rem',
                      fontStyle: 'italic',
                      mt: 0.3,
                    }}
                  >
                    {action.params.program_name}
                  </Typography>
                )}
                
                {/* Line 1: Program time - WHITE, single line with labels (show if available) */}
                {(action.params?.program_start_time || action.params?.program_end_time) && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#ffffff',
                      display: 'block',
                      fontSize: index === 0 ? '0.68rem' : '0.65rem',
                      mt: 0.2,
                    }}
                  >
                    {action.params.program_start_time && `start: ${action.params.program_start_time}`}
                    {action.params.program_start_time && action.params.program_end_time && ' - '}
                    {action.params.program_end_time && `end: ${action.params.program_end_time}`}
                  </Typography>
                )}
                
                {/* Line 2: Durations - WHITE, single line with explicit labels (backend calculated) */}
                {action.params?.total_zap_duration_ms && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#ffffff',
                      display: 'block',
                      fontSize: index === 0 ? '0.68rem' : '0.65rem',
                      mt: 0.2,
                    }}
                  >
                    {/* Use backend-calculated total duration */}
                    {action.params.detection_type === 'automatic'
                      ? `Zap: ${(action.params.total_zap_duration_ms / 1000).toFixed(1)}s - Blackscreen: ${(action.params.blackscreen_duration_ms / 1000).toFixed(1)}s${action.params?.audio_silence_duration ? ` - Silence: ${action.params.audio_silence_duration.toFixed(1)}s` : ''}`
                      : `Blackscreen: ${(action.params.blackscreen_duration_ms / 1000).toFixed(1)}s${action.params?.audio_silence_duration ? ` - Silence: ${action.params.audio_silence_duration.toFixed(1)}s` : ''}`
                    }
                  </Typography>
                )}
              </>
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

