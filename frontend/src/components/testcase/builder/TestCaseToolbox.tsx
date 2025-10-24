import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { toolboxConfig as staticToolboxConfig, CommandConfig } from './toolboxConfig';

interface DraggableCommandProps {
  command: CommandConfig;
}

const DraggableCommand: React.FC<DraggableCommandProps> = ({ command }) => {
  const onDragStart = (event: React.DragEvent) => {
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

interface TestCaseToolboxProps {
  toolboxConfig?: any;  // Optional dynamic config
}

export const TestCaseToolbox: React.FC<TestCaseToolboxProps> = ({ 
  toolboxConfig = staticToolboxConfig  // Fallback to static config
}) => {
  // Define tab colors (same as header tabs before)
  const tabColors: Record<string, string> = {
    'standard': '#3b82f6',    // blue
    'navigation': '#8b5cf6',  // purple
    'actions': '#ef4444',     // red
    'verifications': '#10b981' // green
  };

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* All Tabs - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 0.5,
        }}
      >
        {/* Iterate through all tabs */}
        {Object.keys(toolboxConfig).map((tabKey) => {
          const tabConfig = toolboxConfig[tabKey];
          const tabColor = tabColors[tabKey] || '#6b7280';
          const tabName = tabConfig.tabName || tabKey;

          return (
            <Accordion
              key={tabKey}
              defaultExpanded={false} // Collapsed by default
              sx={{
                boxShadow: 'none',
                '&:before': { display: 'none'},
                padding: '2px !important',
                margin: '4px !important',
                mb: 1,
                borderLeft: `4px solid ${tabColor}`,
                backgroundColor: `${tabColor}08`, // Very subtle background tint
                '& .MuiAccordionDetails-root': {
                  padding: '8px !important',
                  margin: '0px !important',
                },
                '&.Mui-expanded': {
                  padding: '2px !important',
                  margin: '4px !important',
                  minHeight: '0 !important',
                }
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon sx={{ fontSize: 18, color: tabColor }} />}
                sx={{
                  minHeight: '32px !important',
                  height: '32px',
                  py: '0 !important',
                  px: 1,
                  '& .MuiAccordionSummary-content': {
                    my: '0 !important',
                    minHeight: '32px !important',
                  },
                  '&.Mui-expanded': {
                    minHeight: '32px !important',
                    height: '32px',
                    my: '0 !important',
                  }
                }}
              >
                <Typography 
                  fontSize={14} 
                  fontWeight="bold" 
                  sx={{ 
                    color: tabColor,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}
                >
                  {tabName}
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 1 }}>
                {/* All commands from all groups in this tab */}
                {tabConfig.groups.flatMap((group: any) => 
                  group.commands.map((command: any, cmdIdx: number) => (
                    <DraggableCommand key={`${group.groupName}-${cmdIdx}`} command={command} />
                  ))
                )}
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Box>

    </Box>
  );
};

