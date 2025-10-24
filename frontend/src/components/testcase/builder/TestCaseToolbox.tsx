import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useTheme } from '../../../contexts/ThemeContext';
import { toolboxConfig, CommandConfig } from './toolboxConfig';

interface DraggableCommandProps {
  command: CommandConfig;
}

const DraggableCommand: React.FC<DraggableCommandProps> = ({ command }) => {
  const onDragStart = (event: React.DragEvent) => {
    // Store both the type and default data
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
        p: 0.75,
        mb: 0.5,
        cursor: 'grab',
        display: 'flex',
        alignItems: 'center',
        gap: 0.75,
        '&:hover': {
          boxShadow: 2,
          transform: 'translateX(4px)',
        },
        '&:active': {
          cursor: 'grabbing',
        },
        transition: 'all 0.2s',
        borderLeft: `3px solid ${command.color}`,
      }}
      title={command.description}
    >
      <Box sx={{ color: command.color, display: 'flex', alignItems: 'center' }}>
        {command.icon}
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography fontSize={11} noWrap>
          {command.label}
        </Typography>
      </Box>
    </Paper>
  );
};

export const TestCaseToolbox: React.FC = () => {
  const { actualMode } = useTheme();
  const [activeTab, setActiveTab] = useState('standard');

  const tabKeys = Object.keys(toolboxConfig);
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
      {/* Tab Headers */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons={false}
          sx={{
            minHeight: 32,
            '& .MuiTab-root': {
              minHeight: 32,
              fontSize: 10,
              py: 0.5,
              px: 1,
              minWidth: 'auto',
            }
          }}
        >
          {tabKeys.map((key) => (
            <Tab
              key={key}
              label={toolboxConfig[key].tabName}
              value={key}
            />
          ))}
        </Tabs>
      </Box>

      {/* Tab Content - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 0.5,
        }}
      >
        {currentTabConfig.groups.map((group, groupIdx) => (
          <Accordion
            key={groupIdx}
            defaultExpanded
            sx={{
              boxShadow: 'none',
              '&:before': { display: 'none' },
              mb: 0.25,
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon fontSize="small" />}
              sx={{
                minHeight: 24,
                py: 0,
                px: 0.75,
                '& .MuiAccordionSummary-content': {
                  my: 0.25,
                }
              }}
            >
              <Typography fontSize={10} fontWeight="medium" color="text.secondary">
                {group.groupName}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0.25, pt: 0 }}>
              {group.commands.map((command, cmdIdx) => (
                <DraggableCommand key={cmdIdx} command={command} />
              ))}
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>

      {/* Instructions - Compact */}
      <Box
        sx={{
          p: 0.75,
          borderTop: 1,
          borderColor: 'divider',
          background: actualMode === 'dark' ? '#1f2937' : '#f9fafb',
        }}
      >
        <Typography fontSize={9} color="text.secondary">
          <strong>Tip:</strong> Drag commands to canvas
        </Typography>
      </Box>
    </Box>
  );
};

