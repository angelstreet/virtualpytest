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
import { toolboxConfig, CommandConfig } from './toolboxConfig';

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
  activeTab: string;
}

export const TestCaseToolbox: React.FC<TestCaseToolboxProps> = ({ activeTab }) => {
  const currentTabConfig = toolboxConfig[activeTab];

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Tab Content - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 0,
        }}
      >
        {currentTabConfig.groups.map((group, groupIdx) => (
          <Accordion
            key={groupIdx}
            defaultExpanded
            sx={{
              boxShadow: 'none',
              '&:before': { display: 'none'},
              padding: '4px !important',
              margin: '8px !important',
              mb: 1.5,
              '& .MuiAccordionDetails-root': {
                padding: '4px !important',
                margin: '8px !important',
              },
              '&.Mui-expanded': {
                padding: '4px !important',
                margin: '8px !important',
                minHeight: '0 !important',
              }
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ fontSize: 16 }} />}
              sx={{
                minHeight: '20px !important',
                height: '20px',
                py: '0 !important',
                px: 0.5,
                '& .MuiAccordionSummary-content': {
                  my: '1 !important',
                  minHeight: '20px !important',
                },
                '&.Mui-expanded': {
                  minHeight: '20px !important',
                  height: '20px',
                  my: '1 !important',
                }
              }}
            >
              <Typography fontSize={16} fontWeight="bold" color="text.primary">
                {group.groupName}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 4}} >
              {group.commands.map((command, cmdIdx) => (
                <DraggableCommand key={cmdIdx} command={command} />
              ))}
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>

    </Box>
  );
};

