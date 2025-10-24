import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import VerifiedIcon from '@mui/icons-material/Verified';
import { useTheme } from '../../../contexts/ThemeContext';
import { VerificationBlockData } from '../../../types/testcase/TestCase_Types';

/**
 * Verification Block - Executes verifications (image, text, etc.)
 * Has both success and failure output handles
 */
export const VerificationBlock: React.FC<NodeProps> = ({ data, selected, dragging }) => {
  const { actualMode } = useTheme();
  const verificationData = data as VerificationBlockData;
  
  const isConfigured = Boolean(verificationData.command);
  
  return (
    <Box
      sx={{
        minWidth: 180,
        border: selected ? '3px solid #fbbf24' : `2px solid ${actualMode === 'dark' ? '#8b5cf6' : '#7c3aed'}`,
        borderRadius: 2,
        background: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        boxShadow: 2,
        cursor: 'pointer',
        opacity: dragging ? 0.5 : (isConfigured ? 1 : 0.6),
        transition: 'opacity 0.2s',
        '&:hover': {
          boxShadow: 4,
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          background: actualMode === 'dark' ? '#8b5cf6' : '#7c3aed',
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <VerifiedIcon sx={{ color: 'white', fontSize: 18 }} />
        <Typography color="white" fontWeight="bold" fontSize={13}>
          VERIFICATION
        </Typography>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            <Chip
              label={verificationData.verification_type || 'unknown'}
              size="small"
              sx={{ fontSize: 10, height: 20, mb: 0.5 }}
            />
            <Typography fontSize={14} fontWeight="medium">
              {verificationData.command}
            </Typography>
            {verificationData.params && Object.keys(verificationData.params).length > 0 && (
              <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {Object.entries(verificationData.params).slice(0, 2).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key}: ${String(value).substring(0, 15)}...`}
                    size="small"
                    sx={{ fontSize: 10, height: 20 }}
                  />
                ))}
              </Box>
            )}
          </>
        ) : (
          <Typography fontSize={12} color="text.secondary">
            Click to configure
          </Typography>
        )}
      </Box>
      
      {/* Input handle at top */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: actualMode === 'dark' ? '#8b5cf6' : '#7c3aed',
          width: 40,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
          top: -4,
        }}
      />
      
      {/* Output handles at bottom - success and failure rectangles */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="success"
        style={{
          left: '30%',
          background: '#10b981',
          width: 35,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
          bottom: -4,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="failure"
        style={{
          left: '70%',
          background: '#ef4444',
          width: 35,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
          bottom: -4,
        }}
      />
    </Box>
  );
};

