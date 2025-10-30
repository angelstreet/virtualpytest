/**
 * Campaign Block Component
 * 
 * Universal block component for the campaign builder canvas.
 * Renders different types of blocks: testcase, script, terminal (start/success/failure).
 * Supports data linking via draggable output badges and input drop zones.
 */

import React, { useState, memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Collapse,
  Tooltip,
} from '@mui/material';
import {
  AccountTree as TestCaseIcon,
  PlayArrow as ScriptIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Delete as DeleteIcon,
  Link as LinkIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { CampaignNode, CampaignDragData } from '../../../types/pages/CampaignGraph_Types';
import { useCampaignBuilder } from '../../../contexts/campaign/CampaignBuilderContext';

export const CampaignBlock = memo(({ data, id }: NodeProps<CampaignNode['data']>) => {
  const { deleteNode, selectNode, linkOutputToInput, nodes } = useCampaignBuilder();
  const [inputsExpanded, setInputsExpanded] = useState(false);
  const [outputsExpanded, setOutputsExpanded] = useState(false);
  
  const isTerminal = ['start', 'success', 'failure'].includes(id);
  const isTestCase = data.executableType === 'testcase';
  const isScript = data.executableType === 'script';

  // Get colors based on node type
  const getColors = () => {
    if (id === 'start') return { bg: '#e3f2fd', border: '#2196f3', text: '#1976d2' };
    if (id === 'success') return { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32' };
    if (id === 'failure') return { bg: '#ffebee', border: '#f44336', text: '#c62828' };
    if (isTestCase) return { bg: '#f3e5f5', border: '#9c27b0', text: '#7b1fa2' };
    if (isScript) return { bg: '#fff3e0', border: '#ff9800', text: '#ef6c00' };
    return { bg: '#f5f5f5', border: '#9e9e9e', text: '#616161' };
  };

  const colors = getColors();

  // Get icon based on node type
  const getIcon = () => {
    if (isTestCase) return <TestCaseIcon sx={{ color: colors.text }} />;
    if (isScript) return <ScriptIcon sx={{ color: colors.text }} />;
    return null;
  };

  // Handle output badge drag start
  const handleOutputDragStart = (e: React.DragEvent, outputName: string, outputType?: string) => {
    const dragData: CampaignDragData = {
      type: 'output-badge',
      blockId: id,
      outputName,
      outputType,
    };
    e.dataTransfer.setData('application/json', JSON.stringify(dragData));
    e.dataTransfer.effectAllowed = 'link';
  };

  // Handle input drop
  const handleInputDrop = (e: React.DragEvent, inputName: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      const dragData: CampaignDragData = JSON.parse(e.dataTransfer.getData('application/json'));
      
      if (dragData.type === 'output-badge' && dragData.blockId && dragData.outputName) {
        // Prevent linking to self
        if (dragData.blockId === id) {
          console.warn('[@CampaignBlock] Cannot link output to input on same block');
          return;
        }
        
        linkOutputToInput(dragData.blockId, dragData.outputName, id, inputName);
      }
    } catch (error) {
      console.error('[@CampaignBlock] Error handling input drop:', error);
    }
  };

  const handleInputDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'link';
  };

  // Find linked source info for an input
  const getLinkedSourceInfo = (inputName: string) => {
    const input = data.inputs?.find(i => i.name === inputName);
    if (!input?.linkedSource) return null;
    
    const sourceNode = nodes.find(n => n.id === input.linkedSource!.blockId);
    return {
      blockName: sourceNode?.data.label || input.linkedSource.blockId,
      outputName: input.linkedSource.outputName,
    };
  };

  // Handle link icon click (focus on source block)
  const handleLinkIconClick = (inputName: string) => {
    const input = data.inputs?.find(i => i.name === inputName);
    if (input?.linkedSource) {
      selectNode(input.linkedSource.blockId);
      // TODO: Scroll to source block
    }
  };

  // Render terminal nodes (START, SUCCESS, FAILURE)
  if (isTerminal) {
    return (
      <Box
        sx={{
          minWidth: 120,
          minHeight: 60,
          background: colors.bg,
          border: `2px solid ${colors.border}`,
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          color: colors.text,
          fontSize: '1.1rem',
        }}
      >
        {/* Handles */}
        {id === 'start' && (
          <Handle type="source" position={Position.Bottom} style={{ background: colors.border }} />
        )}
        {(id === 'success' || id === 'failure') && (
          <Handle type="target" position={Position.Top} style={{ background: colors.border }} />
        )}
        
        {data.label}
      </Box>
    );
  }

  // Render executable nodes (TestCase, Script)
  return (
    <Box
      sx={{
        minWidth: 280,
        background: '#ffffff',
        border: `2px solid ${colors.border}`,
        borderRadius: 2,
        overflow: 'hidden',
        boxShadow: 2,
        '&:hover': {
          boxShadow: 4,
        },
      }}
      onClick={() => selectNode(id)}
    >
      {/* Handles */}
      <Handle type="target" position={Position.Top} style={{ background: colors.border }} />
      <Handle type="source" position={Position.Bottom} id="pass" style={{ background: '#4caf50', left: '30%' }} />
      <Handle type="source" position={Position.Bottom} id="fail" style={{ background: '#f44336', left: '70%' }} />

      {/* Header */}
      <Box
        sx={{
          p: 1.5,
          background: colors.bg,
          borderBottom: `1px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        {getIcon()}
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: colors.text }}>
            {data.label}
          </Typography>
          {data.executableType && (
            <Typography variant="caption" color="text.secondary">
              {data.executableType === 'testcase' ? 'TestCase' : 'Python Script'}
            </Typography>
          )}
        </Box>
        
        {/* Action Buttons */}
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); /* TODO: Open config dialog */ }}>
          <SettingsIcon fontSize="small" />
        </IconButton>
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); deleteNode(id); }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Body */}
      <Box sx={{ p: 1.5 }}>
        {data.description && (
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            {data.description}
          </Typography>
        )}

        {/* INPUTS Section */}
        {data.inputs && data.inputs.length > 0 && (
          <Box sx={{ mb: 1 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 0.5,
                background: 'rgba(6, 182, 212, 0.05)',
                borderRadius: 1,
                cursor: 'pointer',
              }}
              onClick={() => setInputsExpanded(!inputsExpanded)}
            >
              <Typography 
                variant="caption" 
                sx={{ 
                  fontWeight: 600, 
                  color: '#06b6d4',
                  fontSize: '0.9rem',
                  letterSpacing: '0.5px'
                }}
              >
                INPUTS ({data.inputs.length})
              </Typography>
              {inputsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </Box>
            
            <Collapse in={inputsExpanded}>
              <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {data.inputs.map((input) => {
                  const linkedSource = getLinkedSourceInfo(input.name);
                  
                  return (
                    <Box
                      key={input.name}
                      onDrop={(e) => handleInputDrop(e, input.name)}
                      onDragOver={handleInputDragOver}
                      sx={{
                        p: 0.5,
                        background: linkedSource ? '#e8f5e9' : '#f5f5f5',
                        borderRadius: 1,
                        border: '1px dashed #ccc',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5,
                        '&:hover': {
                          borderColor: '#06b6d4',
                          background: linkedSource ? '#e8f5e9' : 'rgba(6, 182, 212, 0.05)',
                        },
                      }}
                    >
                      <Typography variant="caption" sx={{ flex: 1, fontSize: '0.75rem' }}>
                        {input.name}
                        {input.required && <span style={{ color: '#f44336' }}>*</span>}
                      </Typography>
                      
                      {linkedSource ? (
                        <Tooltip title={`Source: ${linkedSource.blockName} → ${linkedSource.outputName}`}>
                          <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); handleLinkIconClick(input.name); }}
                            sx={{ p: 0.25 }}
                          >
                            <LinkIcon fontSize="small" sx={{ color: '#4caf50' }} />
                          </IconButton>
                        </Tooltip>
                      ) : (
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                          Drop here
                        </Typography>
                      )}
                    </Box>
                  );
                })}
              </Box>
            </Collapse>
          </Box>
        )}

        {/* OUTPUTS Section */}
        {data.outputs && data.outputs.length > 0 && (
          <Box>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 0.5,
                background: 'rgba(249, 115, 22, 0.05)',
                borderRadius: 1,
                cursor: 'pointer',
              }}
              onClick={() => setOutputsExpanded(!outputsExpanded)}
            >
              <Typography 
                variant="caption" 
                sx={{ 
                  fontWeight: 600, 
                  color: '#f97316',
                  fontSize: '0.9rem',
                  letterSpacing: '0.5px'
                }}
              >
                OUTPUTS ({data.outputs.length})
              </Typography>
              {outputsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </Box>
            
            <Collapse in={outputsExpanded}>
              <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {data.outputs.map((output) => (
                  <Chip
                    key={output.name}
                    label={output.name}
                    size="small"
                    draggable
                    onDragStart={(e) => handleOutputDragStart(e, output.name, output.type)}
                    sx={{
                      background: '#f97316',
                      color: 'white',
                      cursor: 'grab',
                      '&:active': {
                        cursor: 'grabbing',
                      },
                      '&:hover': {
                        background: '#ea580c',
                      },
                    }}
                  />
                ))}
              </Box>
            </Collapse>
          </Box>
        )}

        {/* Execution State (during run) */}
        {data.status && (
          <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid #eee' }}>
            <Chip
              label={data.status.toUpperCase()}
              size="small"
              color={
                data.status === 'completed' ? 'success' :
                data.status === 'running' ? 'primary' :
                data.status === 'failed' ? 'error' : 'default'
              }
            />
            {data.executionTime && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                {(data.executionTime / 1000).toFixed(1)}s
              </Typography>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
});

CampaignBlock.displayName = 'CampaignBlock';

