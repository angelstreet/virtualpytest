import React, { useState } from 'react';
import { Box, Typography, Chip, IconButton, Collapse, Select, MenuItem, FormControl } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AddIcon from '@mui/icons-material/Add';
import LinkIcon from '@mui/icons-material/Link';
import CloseIcon from '@mui/icons-material/Close';

interface ScriptInput {
  name: string;
  type: string;
  required: boolean;
  default?: any;
}

interface ScriptOutput {
  name: string;
  type: string;
  sourceBlockId?: string;
  sourceOutputName?: string;
  sourceOutputPath?: string;
}

interface MetadataField {
  name: string;
  sourceBlockId?: string;
  sourceOutputName?: string;
}

interface ScriptIOSectionsProps {
  inputs: ScriptInput[];
  outputs: ScriptOutput[];
  metadata: MetadataField[];
  metadataMode: 'set' | 'append';
  onAddInput: () => void;
  onAddOutput: () => void;
  onAddMetadataField: () => void;
  onRemoveInput: (name: string) => void;
  onRemoveOutput: (name: string) => void;
  onRemoveMetadataField: (name: string) => void;
  onMetadataModeChange: (mode: 'set' | 'append') => void;
  onFocusSourceBlock: (blockId: string) => void;
  onUpdateOutputs: (outputs: ScriptOutput[]) => void;
  onUpdateMetadata: (metadata: MetadataField[]) => void;
}

export const ScriptIOSections: React.FC<ScriptIOSectionsProps> = ({
  inputs,
  outputs,
  metadata,
  metadataMode,
  onAddInput,
  onAddOutput,
  onAddMetadataField,
  onRemoveInput,
  onRemoveOutput,
  onRemoveMetadataField,
  onMetadataModeChange,
  onFocusSourceBlock,
  onUpdateOutputs,
  onUpdateMetadata,
}) => {
  const [inputsExpanded, setInputsExpanded] = useState(false);
  const [outputsExpanded, setOutputsExpanded] = useState(false);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  return (
    <Box sx={{ borderTop: 2, borderColor: 'divider', mt: 'auto' }}>
      {/* INPUTS Section */}
      <Box
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: 'rgba(6, 182, 212, 0.05)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1,
            cursor: 'pointer',
          }}
          onClick={() => setInputsExpanded(!inputsExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="caption"
              fontWeight="bold"
              sx={{ color: '#06b6d4', fontSize: '0.75rem', letterSpacing: '0.5px' }}
            >
              📥 INPUTS ({inputs.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {inputsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={inputsExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {inputs.map((input) => (
              <Chip
                key={input.name}
                label={`${input.name}: ${input.type}${input.required ? ' *' : ''}`}
                size="small"
                onDelete={() => onRemoveInput(input.name)}
                sx={{
                  backgroundColor: '#06b6d4',
                  color: 'white',
                  fontSize: '0.7rem',
                  height: '24px',
                  justifyContent: 'space-between',
                  '& .MuiChip-deleteIcon': { color: 'rgba(255,255,255,0.7)' }
                }}
              />
            ))}
            <Chip
              icon={<AddIcon />}
              label="Add Input"
              size="small"
              onClick={onAddInput}
              sx={{
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                border: '1px dashed #06b6d4',
                color: '#06b6d4',
                fontSize: '0.7rem',
                height: '24px',
              }}
            />
          </Box>
        </Collapse>
      </Box>

      {/* OUTPUTS Section */}
      <Box
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: 'rgba(249, 115, 22, 0.05)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1,
            cursor: 'pointer',
          }}
          onClick={() => setOutputsExpanded(!outputsExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="caption"
              fontWeight="bold"
              sx={{ color: '#f97316', fontSize: '0.75rem', letterSpacing: '0.5px' }}
            >
              📤 OUTPUTS ({outputs.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {outputsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={outputsExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {outputs.map((output) => (
              <Box
                key={output.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                <Box
                  sx={{ flex: 1 }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Get drag data from event
                    const dragData = e.dataTransfer.getData('application/json');
                    if (dragData) {
                      try {
                        const { blockId, outputName, outputType } = JSON.parse(dragData);
                        
                        // Update output with link info
                        const updatedOutputs = outputs.map(o => 
                          o.name === output.name 
                            ? { 
                                ...o, 
                                sourceBlockId: blockId, 
                                sourceOutputName: outputName,
                                sourceOutputType: outputType 
                              }
                            : o
                        );
                        
                        // Trigger parent update
                        onUpdateOutputs(updatedOutputs);
                      } catch (err) {
                        console.error('Failed to parse drag data:', err);
                      }
                    }
                  }}
                >
                  <Chip
                    icon={output.sourceBlockId ? <LinkIcon /> : undefined}
                    label={
                      output.sourceBlockId
                        ? `${output.name} ← ${output.sourceOutputName}`
                        : output.name
                    }
                    size="small"
                    onClick={() => {
                      if (output.sourceBlockId) {
                        onFocusSourceBlock(output.sourceBlockId);
                      }
                    }}
                    sx={{
                      width: '100%',
                      backgroundColor: output.sourceBlockId ? '#10b981' : '#f97316',
                      color: 'white',
                      fontSize: '0.7rem',
                      height: '24px',
                      justifyContent: 'space-between',
                      cursor: output.sourceBlockId ? 'pointer' : 'default',
                      border: '2px dashed transparent',
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                </Box>
                <IconButton
                  size="small"
                  onClick={() => onRemoveOutput(output.name)}
                  sx={{ padding: 0, color: '#ef4444' }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
            <Chip
              icon={<AddIcon />}
              label="Add Output"
              size="small"
              onClick={onAddOutput}
              sx={{
                backgroundColor: 'rgba(249, 115, 22, 0.1)',
                border: '1px dashed #f97316',
                color: '#f97316',
                fontSize: '0.7rem',
                height: '24px',
              }}
            />
          </Box>
        </Collapse>
      </Box>

      {/* METADATA Section */}
      <Box
        sx={{
          backgroundColor: 'rgba(168, 85, 247, 0.05)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1,
            cursor: 'pointer',
          }}
          onClick={() => setMetadataExpanded(!metadataExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="caption"
              fontWeight="bold"
              sx={{ color: '#a855f7', fontSize: '0.75rem', letterSpacing: '0.5px' }}
            >
              💾 METADATA ({metadata.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={metadataExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {/* Mode Selector */}
            <FormControl size="small" fullWidth sx={{ mb: 1 }}>
              <Select
                value={metadataMode}
                onChange={(e) => onMetadataModeChange(e.target.value as 'set' | 'append')}
                sx={{
                  fontSize: '0.75rem',
                  height: '28px',
                  backgroundColor: 'white',
                  '& .MuiSelect-select': { py: 0.5 }
                }}
              >
                <MenuItem value="append" sx={{ fontSize: '0.75rem' }}>Append (Merge)</MenuItem>
                <MenuItem value="set" sx={{ fontSize: '0.75rem' }}>Set (Replace)</MenuItem>
              </Select>
            </FormControl>

            {metadata.map((field) => (
              <Box
                key={field.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                <Box
                  sx={{ flex: 1 }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Get drag data from event
                    const dragData = e.dataTransfer.getData('application/json');
                    if (dragData) {
                      try {
                        const { blockId, outputName, outputType } = JSON.parse(dragData);
                        
                        // Update metadata field with link info
                        const updatedMetadata = metadata.map(f => 
                          f.name === field.name 
                            ? { 
                                ...f, 
                                sourceBlockId: blockId, 
                                sourceOutputName: outputName,
                                sourceOutputType: outputType 
                              }
                            : f
                        );
                        
                        // Trigger parent update
                        onUpdateMetadata(updatedMetadata);
                      } catch (err) {
                        console.error('Failed to parse drag data:', err);
                      }
                    }
                  }}
                >
                  <Chip
                    icon={field.sourceBlockId ? <LinkIcon /> : undefined}
                    label={
                      field.sourceBlockId
                        ? `${field.name} ← ${field.sourceOutputName}`
                        : field.name
                    }
                    size="small"
                    onClick={() => {
                      if (field.sourceBlockId) {
                        onFocusSourceBlock(field.sourceBlockId);
                      }
                    }}
                    sx={{
                      width: '100%',
                      backgroundColor: field.sourceBlockId ? '#10b981' : '#a855f7',
                      color: 'white',
                      fontSize: '0.7rem',
                      height: '24px',
                      justifyContent: 'space-between',
                      cursor: field.sourceBlockId ? 'pointer' : 'default',
                      border: '2px dashed transparent',
                      '& .MuiChip-icon': { color: 'white' }
                    }}
                  />
                </Box>
                <IconButton
                  size="small"
                  onClick={() => onRemoveMetadataField(field.name)}
                  sx={{ padding: 0, color: '#ef4444' }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
            <Chip
              icon={<AddIcon />}
              label="Add Field"
              size="small"
              onClick={onAddMetadataField}
              sx={{
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                border: '1px dashed #a855f7',
                color: '#a855f7',
                fontSize: '0.7rem',
                height: '24px',
              }}
            />
          </Box>
        </Collapse>
      </Box>
    </Box>
  );
};

