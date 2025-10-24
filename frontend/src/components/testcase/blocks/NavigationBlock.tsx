import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import NavigationIcon from '@mui/icons-material/Navigation';
import { useTheme } from '../../../contexts/ThemeContext';
import { NavigationBlockData } from '../../../types/testcase/TestCase_Types';

/**
 * Navigation Block - Executes goto navigation
 * Has both success and failure output handles
 */
export const NavigationBlock: React.FC<NodeProps> = ({ data, selected }) => {
  const { actualMode } = useTheme();
  const navigationData = data as NavigationBlockData;
  
  const isConfigured = Boolean(navigationData.target_node_label);
  
  return (
    <Box
      sx={{
        minWidth: 180,
        border: selected ? '3px solid #fbbf24' : `2px solid ${actualMode === 'dark' ? '#10b981' : '#059669'}`,
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
          background: actualMode === 'dark' ? '#10b981' : '#059669',
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <NavigationIcon sx={{ color: 'white', fontSize: 18 }} />
        <Typography color="white" fontWeight="bold" fontSize={13}>
          NAVIGATION
        </Typography>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            <Typography fontSize={11} color="text.secondary">
              goto
            </Typography>
            <Typography fontSize={14} fontWeight="medium" mt={0.5}>
              {navigationData.target_node_label}
            </Typography>
          </>
        ) : (
          <Typography fontSize={12} color="text.secondary">
            Click to select node
          </Typography>
        )}
      </Box>
      
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: actualMode === 'dark' ? '#10b981' : '#059669',
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

