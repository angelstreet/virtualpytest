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
const HIDDEN_METADATA_FIELDS = ['description', 'default', 'required', 'optional', 'placeholder', 'hidden'];

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

  return (
    <Box sx={{ mb: 1 }} onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 0.5,
          cursor: 'pointer',
          py: 0.5,
          px: 1,
          background: actualMode === 'dark' 
            ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(139, 92, 246, 0.08) 100%)'
            : 'linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(139, 92, 246, 0.06) 100%)',
          borderRadius: 1,
          border: '2px solid',
          borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.4)' : 'rgba(139, 92, 246, 0.3)',
          boxShadow: actualMode === 'dark'
            ? '0 2px 8px rgba(139, 92, 246, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
            : '0 2px 8px rgba(139, 92, 246, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5)',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            bgcolor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)',
            borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.6)' : 'rgba(139, 92, 246, 0.5)',
            boxShadow: actualMode === 'dark'
              ? '0 4px 12px rgba(139, 92, 246, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15)'
              : '0 4px 12px rgba(139, 92, 246, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
            transform: 'translateY(-1px)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, minWidth: 0 }}>
          <Typography fontSize={13} fontWeight="bold" color="#8b5cf6" sx={{ flexShrink: 0 }}>
            INPUTS ({displayParams.length})
          </Typography>
          
          {/* Preview: Show first 1-3 inputs inline when collapsed */}
          {!expanded && (
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 0.5, 
              overflow: 'hidden',
              flex: 1,
              minWidth: 0,
            }}>
              {displayParams.slice(0, 3).map(([key]) => {
                const link = paramLinks?.[key];
                const isLinked = Boolean(link);
                
                return (
                  <Chip
                    key={key}
                    label={key}
                    size="small"
                    icon={isLinked ? <LinkIcon sx={{ fontSize: 10, color: '#10b981' }} /> : undefined}
                    sx={{ 
                      fontSize: 14, 
                      height: 20,
                      maxWidth: '80px',
                      bgcolor: isLinked 
                        ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)')
                        : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.1)' : 'rgba(139, 92, 246, 0.08)'),
                      borderColor: isLinked ? '#10b981' : '#8b5cf6',
                      '& .MuiChip-label': {
                        px: 0.5,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }
                    }}
                    variant="outlined"
                  />
                );
              })}
              {displayParams.length > 3 && (
                <Typography fontSize={9} color="#8b5cf6" sx={{ flexShrink: 0 }}>
                  +{displayParams.length - 3}
                </Typography>
              )}
            </Box>
          )}
        </Box>
        {expanded ? <ExpandLessIcon sx={{ fontSize: 16, color: '#8b5cf6', flexShrink: 0 }} /> : <ExpandMoreIcon sx={{ fontSize: 16, color: '#8b5cf6', flexShrink: 0 }} />}
      </Box>
      
      <Collapse in={expanded}>
        <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
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
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
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
              >
                <Chip
                  label={isLinked && link
                    ? `${key} ← ${link.sourceOutputName}` 
                    : `${key}: ${displayValue.substring(0, 30)}${displayValue.length > 30 ? '...' : ''}`
                  }
                  size="small"
                  icon={isLinked ? <LinkIcon sx={{ fontSize: 12, color: '#10b981' }} /> : undefined}
                  onClick={(e) => {
                    e.stopPropagation(); // ✅ Prevent block selection
                    if (!isLinked) {
                      // ✅ If onConfigureClick provided, open config dialog instead of view dialog
                      if (onConfigureClick) {
                        onConfigureClick();
                      } else {
                        handleViewValue(key, actualValue, e);
                      }
                    }
                  }}
                  onDelete={isLinked && onUnlink ? () => onUnlink(key) : undefined}
                  sx={{ 
                    fontSize: 16, 
                    height: 26,
                    flex: 1,
                    bgcolor: isLinked 
                      ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)')
                      : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.1)' : 'rgba(139, 92, 246, 0.08)'),
                    borderColor: isLinked ? '#10b981' : '#8b5cf6',
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: isLinked
                        ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.2)')
                        : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)'),
                    }
                  }}
                  variant="outlined"
                />
                
                <Tooltip title={copiedParam === key ? "Copied!" : "Copy value"}>
                  <IconButton
                    size="small"
                    onClick={(e) => handleCopyParam(key, actualValue, e)}
                    sx={{
                      padding: '2px',
                      color: copiedParam === key ? '#10b981' : '#8b5cf6',
                      '&:hover': {
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
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

