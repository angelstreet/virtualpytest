import React from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import VerifiedIcon from '@mui/icons-material/Verified';
import NavigationIcon from '@mui/icons-material/Navigation';
import LoopIcon from '@mui/icons-material/Loop';
import { BlockType } from '../../../types/testcase/TestCase_Types';
import { useTheme } from '../../../contexts/ThemeContext';

interface DraggableBlockProps {
  type: BlockType;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const DraggableBlock: React.FC<DraggableBlockProps> = ({ type, label, icon, color }) => {
  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow', type);
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
        transition: 'all 0.2s',
        borderLeft: `3px solid ${color}`,
      }}
    >
      <Box sx={{ color }}>{icon}</Box>
      <Typography fontSize={12}>{label}</Typography>
    </Paper>
  );
};

export const TestCaseToolbox: React.FC = () => {
  const { actualMode } = useTheme();

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        p: 1.5,
        overflowY: 'auto',
      }}
    >
      <Typography variant="subtitle2" mb={1} fontWeight="bold">
        Toolbox
      </Typography>

      {/* Actions */}
      <Accordion defaultExpanded sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />} sx={{ minHeight: 32, py: 0 }}>
          <Typography fontSize={13} fontWeight="medium">
            Actions
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0.5 }}>
          <DraggableBlock
            type={BlockType.ACTION}
            label="Action"
            icon={<PlayArrowIcon fontSize="small" />}
            color="#3b82f6"
          />
        </AccordionDetails>
      </Accordion>

      {/* Verifications */}
      <Accordion defaultExpanded sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />} sx={{ minHeight: 32, py: 0 }}>
          <Typography fontSize={13} fontWeight="medium">
            Verifications
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0.5 }}>
          <DraggableBlock
            type={BlockType.VERIFICATION}
            label="Verification"
            icon={<VerifiedIcon fontSize="small" />}
            color="#8b5cf6"
          />
        </AccordionDetails>
      </Accordion>

      {/* Navigation */}
      <Accordion defaultExpanded sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />} sx={{ minHeight: 32, py: 0 }}>
          <Typography fontSize={13} fontWeight="medium">
            Navigation
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0.5 }}>
          <DraggableBlock
            type={BlockType.NAVIGATION}
            label="Goto"
            icon={<NavigationIcon fontSize="small" />}
            color="#10b981"
          />
        </AccordionDetails>
      </Accordion>

      {/* Control Flow */}
      <Accordion defaultExpanded sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />} sx={{ minHeight: 32, py: 0 }}>
          <Typography fontSize={13} fontWeight="medium">
            Control Flow
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0.5 }}>
          <DraggableBlock
            type={BlockType.LOOP}
            label="Loop"
            icon={<LoopIcon fontSize="small" />}
            color="#f59e0b"
          />
        </AccordionDetails>
      </Accordion>

      {/* Instructions - Compact */}
      <Box sx={{ mt: 1.5, p: 1, background: actualMode === 'dark' ? '#1f2937' : '#ffffff', borderRadius: 1 }}>
        <Typography fontSize={10} color="text.secondary">
          <strong>Instructions:</strong>
          <br />
          • Drag blocks to canvas
          <br />
          • Click to configure
          <br />
          • Green = success, Red = failure
        </Typography>
      </Box>
    </Box>
  );
};

