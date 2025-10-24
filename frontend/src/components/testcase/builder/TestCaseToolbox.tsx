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
        p: 1.5,
        mb: 1,
        cursor: 'grab',
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        '&:hover': {
          boxShadow: 2,
          transform: 'translateX(4px)',
        },
        transition: 'all 0.2s',
        borderLeft: `4px solid ${color}`,
      }}
    >
      <Box sx={{ color }}>{icon}</Box>
      <Typography fontSize={13}>{label}</Typography>
    </Paper>
  );
};

export const TestCaseToolbox: React.FC = () => {
  const { actualMode } = useTheme();

  return (
    <Box
      sx={{
        width: 250,
        borderRight: 1,
        borderColor: 'divider',
        p: 2,
        background: actualMode === 'dark' ? '#111827' : '#f9fafb',
        overflowY: 'auto',
        height: '100%',
      }}
    >
      <Typography variant="h6" mb={2} fontWeight="bold">
        Toolbox
      </Typography>
      <Typography variant="caption" color="text.secondary" mb={2} display="block">
        Drag blocks to canvas
      </Typography>

      {/* Actions */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontSize={14} fontWeight="medium">
            Actions
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 1 }}>
          <DraggableBlock
            type={BlockType.ACTION}
            label="Action"
            icon={<PlayArrowIcon fontSize="small" />}
            color="#3b82f6"
          />
        </AccordionDetails>
      </Accordion>

      {/* Verifications */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontSize={14} fontWeight="medium">
            Verifications
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 1 }}>
          <DraggableBlock
            type={BlockType.VERIFICATION}
            label="Verification"
            icon={<VerifiedIcon fontSize="small" />}
            color="#8b5cf6"
          />
        </AccordionDetails>
      </Accordion>

      {/* Navigation */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontSize={14} fontWeight="medium">
            Navigation
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 1 }}>
          <DraggableBlock
            type={BlockType.NAVIGATION}
            label="Goto"
            icon={<NavigationIcon fontSize="small" />}
            color="#10b981"
          />
        </AccordionDetails>
      </Accordion>

      {/* Control Flow */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontSize={14} fontWeight="medium">
            Control Flow
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 1 }}>
          <DraggableBlock
            type={BlockType.LOOP}
            label="Loop"
            icon={<LoopIcon fontSize="small" />}
            color="#f59e0b"
          />
        </AccordionDetails>
      </Accordion>

      {/* Instructions */}
      <Box sx={{ mt: 3, p: 2, background: actualMode === 'dark' ? '#1f2937' : '#ffffff', borderRadius: 1 }}>
        <Typography fontSize={11} color="text.secondary">
          <strong>Instructions:</strong>
          <br />
          • Drag blocks to canvas
          <br />
          • Click to configure
          <br />
          • Connect outputs to inputs
          <br />
          • Green = success path
          <br />
          • Red = failure path
        </Typography>
      </Box>
    </Box>
  );
};

