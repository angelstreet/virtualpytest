/**
 * OutputDisplay Component
 * 
 * Universal component to display block output data/results
 * Works for: action, verification, navigation, standard blocks
 */

import React, { useState } from 'react';
import { Box, Typography, Chip, Collapse, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useTheme } from '../../../contexts/ThemeContext';

interface OutputDisplayProps {
  blockOutputs?: Array<{ name: string; type: string; value?: any }>;
  onDragStart?: (output: { blockId: string; outputName: string; outputType: string }) => void;
  onDragEnd?: () => void;
  blockId?: string;
}

export const OutputDisplay: React.FC<OutputDisplayProps> = ({
  blockOutputs,
  onDragStart,
  onDragEnd,
  blockId,
}) => {
  const { actualMode } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [copiedOutput, setCopiedOutput] = useState<string | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewDialogData, setViewDialogData] = useState<{ name: string; value: any } | null>(null);

  if (!blockOutputs || blockOutputs.length === 0) {
    return null;
  }

  const handleCopyOutput = (output: { name: string; type: string; value?: any }, e: React.MouseEvent) => {
    e.stopPropagation();
    const textToCopy = output.value !== undefined 
      ? `${output.name}: ${typeof output.value === 'object' ? JSON.stringify(output.value, null, 2) : String(output.value)}`
      : `${output.name}: ${output.type}`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedOutput(output.name);
    setTimeout(() => setCopiedOutput(null), 2000);
  };

  const handleViewOutput = (output: { name: string; value?: any }, e: React.MouseEvent) => {
    e.stopPropagation();
    setViewDialogData({ name: output.name, value: output.value });
    setViewDialogOpen(true);
  };

  return (
    <Box onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          py: 0.5,
          px: 1,
          bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.15)' : 'rgba(249, 115, 22, 0.1)',
          borderRadius: 1,
          border: '1px solid',
          borderColor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.3)' : 'rgba(249, 115, 22, 0.2)',
          '&:hover': {
            bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, minWidth: 0 }}>
          <Typography fontSize={11} fontWeight="bold" color="#f97316" sx={{ flexShrink: 0 }}>
            📤 OUTPUTS ({blockOutputs.length})
          </Typography>
          
          {/* Preview: Show first 1-3 outputs inline when collapsed */}
          {!expanded && (
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 0.5, 
              overflow: 'hidden',
              flex: 1,
              minWidth: 0,
            }}>
              {blockOutputs.slice(0, 3).map((output) => (
                <Chip
                  key={output.name}
                  label={output.name}
                  size="small"
                  sx={{ 
                    fontSize: 9, 
                    height: 18,
                    maxWidth: '80px',
                    bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.08)',
                    borderColor: '#f97316',
                    '& .MuiChip-label': {
                      px: 0.5,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }
                  }}
                  variant="outlined"
                />
              ))}
              {blockOutputs.length > 3 && (
                <Typography fontSize={9} color="#f97316" sx={{ flexShrink: 0 }}>
                  +{blockOutputs.length - 3}
                </Typography>
              )}
            </Box>
          )}
        </Box>
        {expanded ? <ExpandLessIcon sx={{ fontSize: 16, color: '#f97316', flexShrink: 0 }} /> : <ExpandMoreIcon sx={{ fontSize: 16, color: '#f97316', flexShrink: 0 }} />}
      </Box>
      
      <Collapse in={expanded}>
        <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {blockOutputs.map((output) => {
            const hasValue = output.value !== undefined;
            const displayValue = hasValue
              ? typeof output.value === 'object'
                ? JSON.stringify(output.value, null, 2)
                : String(output.value)
              : output.type;
            
            return (
              <Box key={output.name} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Tooltip 
                  title={
                    hasValue 
                      ? "Click to view • Drag to link to inputs" 
                      : (blockId && onDragStart ? "Drag to link to inputs" : "")
                  }
                  placement="left"
                >
                  <Chip
                    label={hasValue ? `${output.name}: ${displayValue.substring(0, 30)}${displayValue.length > 30 ? '...' : ''}` : `${output.name}: ${output.type}`}
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent block selection
                      // Only handle click if not dragging
                      if (hasValue && !e.defaultPrevented) {
                        handleViewOutput(output, e);
                      }
                    }}
                    draggable={Boolean(blockId && onDragStart)}
                    onDragStart={(e) => {
                      e.stopPropagation(); // ✅ Prevent block drag
                      if (blockId && onDragStart) {
                        const dragData = {
                          blockId: blockId,
                          outputName: output.name,
                          outputType: output.type
                        };
                        onDragStart(dragData);
                        e.dataTransfer.setData('application/json', JSON.stringify(dragData));
                        e.dataTransfer.effectAllowed = 'link';
                      }
                    }}
                    onDrag={(e) => {
                      e.stopPropagation(); // ✅ Prevent block drag during drag
                    }}
                    onDragEnd={(e) => {
                      e.stopPropagation(); // ✅ Prevent block drag on end
                      if (onDragEnd) {
                        onDragEnd();
                      }
                    }}
                    sx={{ 
                      fontSize: 10, 
                      height: 24,
                      flex: 1,
                      bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.08)',
                      borderColor: '#f97316',
                      cursor: blockId && onDragStart ? 'grab' : (hasValue ? 'pointer' : 'default'),
                      '&:hover': {
                        bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
                      },
                      '&:active': {
                        cursor: blockId && onDragStart ? 'grabbing' : (hasValue ? 'pointer' : 'default'),
                      }
                    }}
                    variant="outlined"
                  />
                </Tooltip>
                
                <Tooltip title={copiedOutput === output.name ? "Copied!" : "Copy output"}>
                  <IconButton
                    size="small"
                    onClick={(e) => handleCopyOutput(output, e)}
                    sx={{
                      padding: '2px',
                      color: copiedOutput === output.name ? '#10b981' : '#f97316',
                      '&:hover': {
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                      },
                    }}
                  >
                    <ContentCopyIcon sx={{ fontSize: 12 }} />
                  </IconButton>
                </Tooltip>
              </Box>
            );
          })}
        </Box>
      </Collapse>
      
      {/* View Value Dialog */}
      <Dialog 
        open={viewDialogOpen} 
        onClose={() => setViewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {viewDialogData?.name}
        </DialogTitle>
        <DialogContent>
          <Box
            sx={{
              backgroundColor: actualMode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.05)',
              borderRadius: 1,
              p: 2,
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              maxHeight: '400px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {viewDialogData && (
              viewDialogData.value !== undefined
                ? (typeof viewDialogData.value === 'object'
                    ? JSON.stringify(viewDialogData.value, null, 2)
                    : String(viewDialogData.value))
                : 'No value available'
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            if (viewDialogData && viewDialogData.value !== undefined) {
              const textToCopy = typeof viewDialogData.value === 'object'
                ? JSON.stringify(viewDialogData.value, null, 2)
                : String(viewDialogData.value);
              navigator.clipboard.writeText(textToCopy);
            }
          }}>
            Copy
          </Button>
          <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

