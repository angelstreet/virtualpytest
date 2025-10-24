import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import LoopIcon from '@mui/icons-material/Loop';
import { useTheme } from '../../../contexts/ThemeContext';
import { LoopBlockData } from '../../../types/testcase/TestCase_Types';

/**
 * Loop Block - Container for repeated execution
 * Double-click to enter nested view
 * Has both success and failure output handles
 */
export const LoopBlock: React.FC<NodeProps> = ({ data, selected }) => {
  const { actualMode } = useTheme();
  const loopData = data as LoopBlockData;
  
  const isConfigured = loopData.iterations > 0;
  const blockCount = loopData.nested_graph?.nodes?.length || 0;
  
  return (
    <Box
      sx={{
        minWidth: 200,
        border: selected ? '3px solid #fbbf24' : `2px solid ${actualMode === 'dark' ? '#f59e0b' : '#d97706'}`,
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
          background: actualMode === 'dark' ? '#f59e0b' : '#d97706',
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <LoopIcon sx={{ color: 'white', fontSize: 18 }} />
        <Typography color="white" fontWeight="bold" fontSize={13}>
          LOOP
        </Typography>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            <Typography fontSize={14} fontWeight="medium">
              {loopData.iterations} iteration{loopData.iterations !== 1 ? 's' : ''}
            </Typography>
            <Box
              sx={{
                mt: 1,
                p: 1,
                border: '1px dashed',
                borderColor: actualMode === 'dark' ? '#374151' : '#d1d5db',
                borderRadius: 1,
                textAlign: 'center',
              }}
            >
              <Typography fontSize={11} color="text.secondary">
                {blockCount} block{blockCount !== 1 ? 's' : ''} inside
              </Typography>
              <Typography fontSize={10} color="text.secondary" mt={0.5}>
                Double-click to edit
              </Typography>
            </Box>
          </>
        ) : (
          <Typography fontSize={12} color="text.secondary">
            Click to configure loop
          </Typography>
        )}
      </Box>
      
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: actualMode === 'dark' ? '#f59e0b' : '#d97706',
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

