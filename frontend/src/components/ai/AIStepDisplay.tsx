/**
 * Shared AI Step Display Component
 * 
 * Displays AI plan steps in consistent command format across:
 * - Live AI execution panel
 * - Test case generation preview
 * - Test case editor details
 * 
 * Features:
 * - Shows command format (not AI descriptions)
 * - Expandable navigation steps with PRE-FETCHED transitions (no API calls)
 * - Status indicators (pending/current/completed/failed)
 * 
 * IMPORTANT: Transitions are ALWAYS pre-fetched during plan generation.
 * No fallback, no legacy, no API fetching in UI.
 */

import React, { useState } from 'react';
import { Box, Typography, IconButton, CircularProgress } from '@mui/material';
import { ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';

interface AIStepDisplayProps {
  step: {
    stepNumber: number;
    command: string;
    params?: any;
    description?: string;
    type?: string;
    status?: 'pending' | 'current' | 'completed' | 'failed';
    duration?: number;
    transitions?: any[]; // PRE-FETCHED transitions - always available, no UI fetching
  };
  showExpand?: boolean; // Default true
  compact?: boolean; // Compact mode for lists
}

export const AIStepDisplay: React.FC<AIStepDisplayProps> = ({
  step,
  showExpand = true,
  compact = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const isNavigation = step.command === 'execute_navigation';
  const transitions = step.transitions || []; // PRE-FETCHED - always available
  
  // DEBUG: Log step data to see if duration exists
  console.log(`[@AIStepDisplay] Step ${step.stepNumber}:`, {
    status: step.status,
    duration: step.duration,
    has_duration: !!step.duration,
    full_step: step
  });

  // Status styling
  const getStatusStyle = () => {
    const { status } = step;
    
    let statusIcon, bgColor, borderColor;
    if (status === 'completed') {
      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#4caf50' }} />;
      bgColor = 'rgba(76,175,80,0.1)';
      borderColor = 'rgba(76,175,80,0.3)';
    } else if (status === 'failed') {
      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#f44336' }} />;
      bgColor = 'rgba(244,67,54,0.1)';
      borderColor = 'rgba(244,67,54,0.3)';
    } else if (status === 'current') {
      statusIcon = <CircularProgress size={12} sx={{ color: '#2196f3' }} />;
      bgColor = 'rgba(33,150,243,0.1)';
      borderColor = 'rgba(33,150,243,0.3)';
    } else {
      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#666', border: '1px solid #888' }} />;
      bgColor = 'rgba(255,255,255,0.05)';
      borderColor = 'transparent';
    }

    return { statusIcon, bgColor, borderColor };
  };

  const { statusIcon, bgColor, borderColor } = getStatusStyle();

  // Display text: command format for navigation, description for others
  const displayText = isNavigation 
    ? `${step.command}(${step.params?.target_node || 'unknown'})`
    : step.description || step.command;

  // Simple toggle - transitions are ALWAYS pre-fetched, no API calls needed
  const handleToggleExpand = () => {
    if (!isNavigation) return;
    setIsExpanded(!isExpanded);
  };

  return (
    <Box
      sx={{
        mb: compact ? 0.5 : 1,
        p: compact ? 0.5 : 1,
        backgroundColor: bgColor,
        borderRadius: 0.5,
        border: `1px solid ${borderColor}`,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        {statusIcon}
        <Typography 
          variant="caption" 
          sx={{ 
            color: '#fff', 
            fontWeight: 'bold', 
            fontFamily: isNavigation ? 'monospace' : 'inherit',
            flex: 1,
            fontSize: compact ? '0.75rem' : '0.875rem'
          }}
        >
          {step.stepNumber}. {displayText}
          {step.duration && ` (${step.duration.toFixed(1)}s)`}
        </Typography>
        
        {isNavigation && showExpand && (
          <IconButton 
            size="small"
            onClick={handleToggleExpand}
            sx={{ color: '#aaa', p: 0.25 }}
          >
            {isExpanded ? (
              <ExpandLessIcon fontSize="small" />
            ) : (
              <ExpandMoreIcon fontSize="small" />
            )}
          </IconButton>
        )}
      </Box>
      
      {/* Navigation transitions (when expanded) */}
      {isNavigation && isExpanded && transitions.length > 0 && (
        <Box sx={{ ml: 2, mt: 1, borderLeft: '2px solid #444', pl: 1 }}>
          {transitions.map((transition: any, tIdx: number) => (
            <Box key={tIdx} sx={{ mb: 1 }}>
              <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 'bold', display: 'block' }}>
                {transition.from_node_label} → {transition.to_node_label}
              </Typography>
              {transition.actions?.map((action: any, aIdx: number) => {
                const firstParam = action.params ? Object.values(action.params)[0] : '';
                const paramStr = typeof firstParam === 'string' ? firstParam : JSON.stringify(firstParam);
                return (
                  <Typography key={aIdx} variant="caption" sx={{ color: '#aaa', display: 'block', ml: 1, fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    - {action.command}({paramStr})
                  </Typography>
                );
              })}
              {transition.verifications?.length > 0 && (
                <Box sx={{ ml: 1, mt: 0.5 }}>
                  <Typography variant="caption" sx={{ color: '#888', fontSize: '0.65rem' }}>Verifications:</Typography>
                  {transition.verifications.map((verification: any, vIdx: number) => (
                    <Typography key={vIdx} variant="caption" sx={{ color: '#888', display: 'block', ml: 1, fontFamily: 'monospace', fontSize: '0.65rem' }}>
                      - {verification.command} ({verification.verification_type})
                    </Typography>
                  ))}
                </Box>
              )}
            </Box>
          ))}
        </Box>
      )}
      
      {/* Non-navigation steps: show command/params */}
      {!isNavigation && (
        <Typography variant="caption" sx={{ color: '#aaa', display: 'block', ml: 2, fontFamily: 'monospace', fontSize: compact ? '0.65rem' : '0.75rem' }}>
          {step.command}
          {step.params && Object.keys(step.params).length > 0 && ` | ${JSON.stringify(step.params)}`}
        </Typography>
      )}
    </Box>
  );
};
