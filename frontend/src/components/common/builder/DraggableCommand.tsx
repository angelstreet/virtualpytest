/**
 * Shared Draggable Command Component
 * 
 * Extracted from TestCaseToolbox - now used by both TestCase and Campaign builders.
 * Renders a draggable command block from the toolbox configuration.
 */

import React from 'react';
import { Paper, Typography } from '@mui/material';
import { CommandConfig } from '../../testcase/builder/toolboxConfig';

interface DraggableCommandProps {
  command: CommandConfig;
  onCloseProgressBar?: () => void;
}

export const DraggableCommand: React.FC<DraggableCommandProps> = ({ command, onCloseProgressBar }) => {
  const onDragStart = (event: React.DragEvent) => {
    // Close progress bar when starting to drag a command
    onCloseProgressBar?.();
    
    const dragData = JSON.stringify({
      type: command.type,
      defaultData: command.defaultData || {}
    });
    event.dataTransfer.setData('application/reactflow', dragData);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Paper
      onDragStart={onDragStart}
      draggable
      sx={{
        py: 0.5,
        px: 0.5,
        mb: 0.5,
        cursor: 'grab',
        display: 'flex',
        alignItems: 'center',
        lineHeight: 1.5,
        minHeight: '0 !important',
        height: 'auto',
        '&:hover': {
          boxShadow: 1,
          transform: 'translateX(12px)',
        },
        '&:active': {
          cursor: 'grabbing',
        },
        transition: 'all 0.15s',
        borderLeft: `3px solid ${command.color}`,
      }}
      title={command.description}
    >
      <Typography fontSize={13} noWrap sx={{ lineHeight: 1, mb: 0 }}>
        {command.label}
      </Typography>
    </Paper>
  );
};

