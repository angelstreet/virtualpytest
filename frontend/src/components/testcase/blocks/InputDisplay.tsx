/**
 * InputDisplay Component
 * 
 * Universal component to display block input parameters
 * Works for: action, verification, navigation, standard blocks
 */

import React, { useState } from 'react';
import { Box, Typography, Chip, Collapse, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import LinkIcon from '@mui/icons-material/Link';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useTheme } from '../../../contexts/ThemeContext';

// Metadata fields to hide from parameter display
const HIDDEN_METADATA_FIELDS = ['description', 'default', 'key', 'type', 'required', 'optional', 'placeholder', 'hidden', 'min', 'max'];

// Commands that dump entire device - don't need area parameter
const DUMP_COMMANDS = ['getMenuInfo', 'dumpWindowHierarchy', 'dumpUI', 'getUIElements'];

interface InputDisplayProps {
  params?: Record<string, any>;
  paramLinks?: Record<string, {
    sourceBlockId: string;
    sourceOutputName: string;
    sourceOutputType: string;
  }>;
  onDrop?: (paramKey: string, dragData: { blockId: string; outputName: string; outputType: string }) => void;
  onUnlink?: (paramKey: string) => void;
  draggedOutput?: { blockId: string; outputName: string; outputType: string } | null;
  command?: string; // ✅ Add command to know which params to hide
  onConfigureClick?: () => void; // ✅ NEW: Callback to open config dialog
}

export const InputDisplay: React.FC<InputDisplayProps> = ({
  params,
  paramLinks,
  onDrop,
  onUnlink,
  draggedOutput,
  command,
  onConfigureClick, // ✅ NEW
}) => {
  // ✅ ALWAYS call hooks at the top level - before any early returns
  const { actualMode } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [copiedParam, setCopiedParam] = useState<string | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewDialogData, setViewDialogData] = useState<{ key: string; value: any } | null>(null);

  // Filter out metadata fields and command-specific hidden params
  const isDumpCommand = command && DUMP_COMMANDS.includes(command);
  const displayParams = params 
    ? Object.entries(params).filter(([key]) => {
        // Always hide metadata fields
        if (HIDDEN_METADATA_FIELDS.includes(key)) return false;
        
        // Hide 'area' for dump commands (they scan the entire device)
        if (isDumpCommand && key === 'area') return false;
        
        return true;
      })
    : [];

  // Early return AFTER all hooks
  if (displayParams.length === 0) {
    return null;
  }

  const handleCopyParam = (key: string, value: any, e: React.MouseEvent) => {
    e.stopPropagation();
    const textToCopy = `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedParam(key);
    setTimeout(() => setCopiedParam(null), 2000);
  };

  const handleViewValue = (key: string, value: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setViewDialogData({ key, value });
    setViewDialogOpen(true);
  };

  const getValueType = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object') return 'dict';
    if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
    return typeof value; // string, boolean, etc.
  };

  // Accent color for inputs
  const inputColor = '#7c3aed'; // muted violet

  return (
    <Box sx={{ mb: 0.5 }} onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          cursor: 'pointer',
          py: 0.25,
          px: 0.5,
          borderRadius: 0.5,
          transition: 'background 0.15s ease',
          '&:hover': {
            bgcolor: actualMode === 'dark' ? 'rgba(124, 58, 237, 0.1)' : 'rgba(124, 58, 237, 0.05)',
          },
        }}
      >
        <Typography fontSize={10} fontWeight={500} color={inputColor} sx={{ opacity: 0.8 }}>
          ↳
        </Typography>
        
        {/* Inline params preview */}
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 0.5, 
          overflow: 'hidden',
          flex: 1,
          minWidth: 0,
        }}>
          {displayParams.slice(0, expanded ? displayParams.length : 4).map(([key]) => {
            const link = paramLinks?.[key];
            const isLinked = Boolean(link);
            
            return (
              <Typography
                key={key}
                fontSize={10}
                sx={{ 
                  color: isLinked ? '#16a34a' : 'text.secondary',
                  fontWeight: isLinked ? 500 : 400,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '60px',
                }}
              >
                {key}
              </Typography>
            );
          })}
          {!expanded && displayParams.length > 4 && (
            <Typography fontSize={9} color="text.disabled">
              +{displayParams.length - 4}
            </Typography>
          )}
        </Box>
        
        <IconButton size="small" sx={{ p: 0, opacity: 0.5 }}>
          {expanded ? <ExpandLessIcon sx={{ fontSize: 12, color: 'text.secondary' }} /> : <ExpandMoreIcon sx={{ fontSize: 12, color: 'text.secondary' }} />}
        </IconButton>
      </Box>
      
      <Collapse in={expanded}>
        <Box sx={{ mt: 0.25, pl: 1.5, display: 'flex', flexDirection: 'column', gap: 0.25 }}>
          {displayParams.map(([key, value]) => {
            const link = paramLinks?.[key];
            const isLinked = Boolean(link);
            
            // Extract actual value from object structure
            let actualValue = value;
            if (typeof value === 'object' && value !== null) {
              actualValue = (value as any).value !== undefined ? (value as any).value : value;
              
              if (typeof actualValue === 'object' && actualValue !== null) {
                const filtered: Record<string, any> = {};
                Object.entries(actualValue).forEach(([k, v]) => {
                  if (!HIDDEN_METADATA_FIELDS.includes(k)) {
                    filtered[k] = v;
                  }
                });
                if (Object.keys(filtered).length === 0 && (value as any).value !== undefined) {
                  actualValue = (value as any).value;
                } else {
                  actualValue = filtered;
                }
              }
            }
            
            const displayValue = typeof actualValue === 'object' 
              ? JSON.stringify(actualValue) 
              : String(actualValue);
            
            return (
              <Box 
                key={key} 
                sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 0.5,
                  py: 0.25,
                  px: 0.5,
                  borderRadius: 0.5,
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                  },
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (draggedOutput && onDrop) {
                    onDrop(key, draggedOutput);
                  }
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (!isLinked) {
                    if (onConfigureClick) {
                      onConfigureClick();
                    } else {
                      handleViewValue(key, actualValue, e);
                    }
                  }
                }}
              >
                {isLinked && <LinkIcon sx={{ fontSize: 10, color: '#16a34a' }} />}
                <Typography 
                  fontSize={10} 
                  sx={{ 
                    color: isLinked ? '#16a34a' : 'text.secondary',
                    fontWeight: isLinked ? 500 : 400,
                  }}
                >
                  {key}
                </Typography>
                {!isLinked && (
                  <Typography 
                    fontSize={10} 
                    sx={{ 
                      color: 'text.disabled',
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    : {displayValue.substring(0, 20)}{displayValue.length > 20 ? '...' : ''}
                  </Typography>
                )}
                {isLinked && link && (
                  <Typography 
                    fontSize={9} 
                    sx={{ color: 'text.disabled' }}
                  >
                    ← {link.sourceOutputName}
                  </Typography>
                )}
                
                <Tooltip title={copiedParam === key ? "Copied!" : "Copy"}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCopyParam(key, actualValue, e);
                    }}
                    sx={{
                      padding: '1px',
                      opacity: 0.5,
                      '&:hover': { opacity: 1 },
                    }}
                  >
                    <ContentCopyIcon sx={{ fontSize: 10, color: copiedParam === key ? '#16a34a' : 'text.secondary' }} />
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
        PaperProps={{
          sx: {
            borderRadius: 2,
            border: '2px solid',
            borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.5)' : 'rgba(139, 92, 246, 0.4)',
            background: actualMode === 'dark'
              ? 'linear-gradient(135deg, rgba(30, 30, 30, 0.98) 0%, rgba(40, 40, 40, 0.98) 100%)'
              : 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 248, 248, 0.98) 100%)',
            boxShadow: actualMode === 'dark'
              ? '0 8px 32px rgba(139, 92, 246, 0.3), 0 0 0 1px rgba(139, 92, 246, 0.2) inset'
              : '0 8px 32px rgba(139, 92, 246, 0.2), 0 0 0 1px rgba(139, 92, 246, 0.1) inset',
          }
        }}
      >
        <DialogTitle
          sx={{
            background: actualMode === 'dark'
              ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(139, 92, 246, 0.08) 100%)'
              : 'linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(139, 92, 246, 0.06) 100%)',
            borderBottom: '2px solid',
            borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.3)' : 'rgba(139, 92, 246, 0.2)',
            color: '#8b5cf6',
            fontWeight: 600,
            fontSize: '1.1rem',
            py: 2,
            mb: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{viewDialogData?.key}</span>
          {viewDialogData && (
            <Chip
              label={getValueType(viewDialogData.value)}
              size="small"
              sx={{
                fontSize: '0.7rem',
                height: '20px',
                fontWeight: 500,
                textTransform: 'uppercase',
                bgcolor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.25)' : 'rgba(139, 92, 246, 0.15)',
                color: '#8b5cf6',
                border: '1px solid',
                borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.4)' : 'rgba(139, 92, 246, 0.3)',
              }}
            />
          )}
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Box
            sx={{
              background: actualMode === 'dark' 
                ? 'linear-gradient(135deg, rgba(0, 0, 0, 0.4) 0%, rgba(20, 20, 20, 0.4) 100%)'
                : 'linear-gradient(135deg, rgba(0, 0, 0, 0.05) 0%, rgba(240, 240, 240, 0.5) 100%)',
              borderRadius: 2,
              border: '1px solid',
              borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)',
              p: 2.5,
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              maxHeight: '400px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              boxShadow: actualMode === 'dark'
                ? 'inset 0 2px 8px rgba(0, 0, 0, 0.3)'
                : 'inset 0 2px 8px rgba(0, 0, 0, 0.08)',
              '&::-webkit-scrollbar': {
                width: '8px',
              },
              '&::-webkit-scrollbar-track': {
                background: actualMode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.05)',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.4)' : 'rgba(139, 92, 246, 0.3)',
                borderRadius: '4px',
                '&:hover': {
                  background: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.6)' : 'rgba(139, 92, 246, 0.5)',
                },
              },
            }}
          >
            {viewDialogData && (
              typeof viewDialogData.value === 'object'
                ? JSON.stringify(viewDialogData.value, null, 2)
                : String(viewDialogData.value)
            )}
          </Box>
        </DialogContent>
        <DialogActions
          sx={{
            borderTop: '1px solid',
            borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)',
            px: 3,
            py: 2,
            gap: 1,
          }}
        >
          <Button 
            onClick={() => {
              if (viewDialogData) {
                const textToCopy = typeof viewDialogData.value === 'object'
                  ? JSON.stringify(viewDialogData.value, null, 2)
                  : String(viewDialogData.value);
                navigator.clipboard.writeText(textToCopy);
              }
            }}
            variant="outlined"
            sx={{
              borderColor: '#8b5cf6',
              color: '#8b5cf6',
              '&:hover': {
                borderColor: '#7c3aed',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
              },
            }}
          >
            Copy
          </Button>
          <Button 
            onClick={() => setViewDialogOpen(false)}
            variant="contained"
            sx={{
              backgroundColor: '#8b5cf6',
              '&:hover': {
                backgroundColor: '#7c3aed',
              },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

