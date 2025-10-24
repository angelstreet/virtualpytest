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
        p: 0.5,
        mb: 0.25,
        cursor: 'grab',
        display: 'flex',
        alignItems: 'center',
        '&:hover': {
          boxShadow: 1,
          transform: 'translateX(2px)',
        },
        '&:active': {
          cursor: 'grabbing',
        },
        transition: 'all 0.15s',
        borderLeft: `2px solid ${command.color}`,
      }}
      title={command.description}
    >
      <Typography fontSize={10} noWrap>
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
          p: 0.25,
        }}
      >
        {currentTabConfig.groups.map((group, groupIdx) => (
          <Accordion
            key={groupIdx}
            defaultExpanded
            sx={{
              boxShadow: 'none',
              '&:before': { display: 'none' },
              mb: 0,
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ fontSize: 16 }} />}
              sx={{
                minHeight: 20,
                py: 0,
                px: 0.5,
                '& .MuiAccordionSummary-content': {
                  my: 0.25,
                }
              }}
            >
              <Typography fontSize={9} fontWeight="medium" color="text.secondary">
                {group.groupName}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0, px: 0.25, pt: 0 }}>
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

