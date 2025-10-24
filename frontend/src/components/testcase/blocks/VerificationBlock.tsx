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
export const VerificationBlock: React.FC<NodeProps> = ({ data, selected }) => {
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
        '&:hover': {
          boxShadow: 4,
        },
        opacity: isConfigured ? 1 : 0.6,
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
      
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: actualMode === 'dark' ? '#8b5cf6' : '#7c3aed',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
      
      {/* Output handles - success and failure */}
      <Handle
        type="source"
        position={Position.Right}
        id="success"
        style={{
          top: '30%',
          background: '#10b981',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="failure"
        style={{
          top: '70%',
          background: '#ef4444',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
    </Box>
  );
};

