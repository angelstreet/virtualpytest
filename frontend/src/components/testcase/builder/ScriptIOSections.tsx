import React, { useState } from 'react';
import { Box, Typography, Chip, IconButton, Collapse, TextField } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AddIcon from '@mui/icons-material/Add';
import LinkIcon from '@mui/icons-material/Link';
import CloseIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';
import { VerificationConfigDialog } from '../dialogs/VerificationConfigDialog';
import { useTestCaseBuilder as useTestCaseBuilderContext } from '../../../contexts/testcase/TestCaseBuilderContext';

interface ScriptInput {
  name: string;
  type: string;
  required: boolean;
  default?: any;
  protected?: boolean; // Protected inputs cannot be deleted
}

interface ScriptOutput {
  name: string;
  type: string;
  sourceBlockId?: string;
  sourceOutputName?: string;
  sourceOutputPath?: string;
}

interface Variable {
  name: string;
  type: string;
  value?: any; // Direct static value (if not linked)
  sourceBlockId?: string; // OR linked to input/output/block
  sourceOutputName?: string;
  sourceOutputType?: string;
}

interface MetadataField {
  name: string;
  value?: any; // Direct value (if not linked)
  sourceBlockId?: string; // OR linked to block output/variable
  sourceOutputName?: string;
  sourceOutputType?: string;
}

interface ScriptIOSectionsProps {
  inputs: ScriptInput[];
  outputs: ScriptOutput[];
  variables: Variable[];
  metadata: MetadataField[];
  onAddInput: () => void;
  onAddOutput: () => void;
  onAddVariable: () => void;
  onAddMetadataField: () => void;
  onRemoveInput: (name: string) => void;
  onRemoveOutput: (name: string) => void;
  onRemoveVariable: (name: string) => void;
  onRemoveMetadataField: (name: string) => void;
  onFocusSourceBlock: (blockId: string) => void;
  onUpdateOutputs: (outputs: ScriptOutput[]) => void;
  onUpdateVariables: (variables: Variable[]) => void;
  onUpdateMetadata: (metadata: MetadataField[]) => void;
}

export const ScriptIOSections: React.FC<ScriptIOSectionsProps> = ({
  inputs,
  outputs,
  variables,
  metadata,
  onAddInput,
  onAddOutput,
  onAddVariable,
  onAddMetadataField,
  onRemoveInput,
  onRemoveOutput,
  onRemoveVariable,
  onRemoveMetadataField,
  onFocusSourceBlock,
  onUpdateOutputs,
  onUpdateVariables,
  onUpdateMetadata,
}) => {
  const [inputsExpanded, setInputsExpanded] = useState(false);
  const [outputsExpanded, setOutputsExpanded] = useState(false);
  const [variablesExpanded, setVariablesExpanded] = useState(false);
  const [metadataExpanded, setMetadataExpanded] = useState(false);
  
  // Editing state
  const [editingMetadataField, setEditingMetadataField] = useState<string | null>(null);
  const [editingVariableName, setEditingVariableName] = useState<string | null>(null);
  const [editingOutputName, setEditingOutputName] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  
  // Dialog state for showing output values
  const [valueDialogOpen, setValueDialogOpen] = useState(false);
  const [selectedOutput, setSelectedOutput] = useState<ScriptOutput | null>(null);
  
  // Get execution values from context
  const { executionOutputValues } = useTestCaseBuilderContext();
  
  const handleOutputClick = (output: ScriptOutput) => {
    setSelectedOutput(output);
    setValueDialogOpen(true);
  };

  const handleStartEditMetadata = (fieldName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingMetadataField(fieldName);
    setEditValue(fieldName);
  };

  const handleSaveMetadataEdit = (oldName: string) => {
    if (editValue && editValue !== oldName) {
      const updatedMetadata = metadata.map(f => 
        f.name === oldName ? { ...f, name: editValue } : f
      );
      onUpdateMetadata(updatedMetadata);
    }
    setEditingMetadataField(null);
    setEditValue('');
  };

  const handleStartEditVariable = (variableName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingVariableName(variableName);
    setEditValue(variableName);
  };

  const handleSaveVariableEdit = (oldName: string) => {
    if (editValue && editValue !== oldName) {
      const updatedVariables = variables.map(v => 
        v.name === oldName ? { ...v, name: editValue } : v
      );
      onUpdateVariables(updatedVariables);
    }
    setEditingVariableName(null);
    setEditValue('');
  };

  const handleStartEditOutput = (outputName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingOutputName(outputName);
    setEditValue(outputName);
  };

  const handleSaveOutputEdit = (oldName: string) => {
    if (editValue && editValue !== oldName) {
      const updatedOutputs = outputs.map(o => 
        o.name === oldName ? { ...o, name: editValue } : o
      );
      onUpdateOutputs(updatedOutputs);
    }
    setEditingOutputName(null);
    setEditValue('');
  };

  return (
    <Box sx={{ borderTop: 2, borderColor: 'divider', mt: 'auto' }}>
      {/* Output Value Dialog - Reusing VerificationConfigDialog */}
      <VerificationConfigDialog
        open={valueDialogOpen}
        onCancel={() => setValueDialogOpen(false)}
        onSave={() => {}}
        mode="viewValue"
        outputName={selectedOutput?.name}
        outputValue={selectedOutput ? executionOutputValues[selectedOutput.name] : undefined}
      />
      
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
              sx={{ color: '#06b6d4', fontSize: '0.9rem', letterSpacing: '0.5px' }}
            >
              INPUTS ({inputs.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {inputsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={inputsExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {inputs.map((input) => {
              // Display label: remove "_name" suffix if present
              let displayName = input.name.endsWith('_name') 
                ? input.name.slice(0, -5) 
                : input.name;
              
              // Special case: rename userinterface to interface
              if (displayName === 'userinterface') {
                displayName = 'interface';
              }
              
              // Display value: show default value if available, otherwise show type
              const displayValue = input.default !== undefined && input.default !== '' 
                ? `${input.default}` 
                : input.type;
              
              return (
                <Chip
                  key={input.name}
                  label={`${displayName}: ${displayValue}`}
                  size="small"
                  draggable
                  onDragStart={(e) => {
                    e.stopPropagation();
                    const dragData = {
                      blockId: 'script_inputs',
                      outputName: input.name,
                      outputType: input.type
                    };
                    e.dataTransfer.setData('application/json', JSON.stringify(dragData));
                    e.dataTransfer.effectAllowed = 'link';
                  }}
                  onDelete={input.protected ? undefined : () => onRemoveInput(input.name)}
                  sx={{
                    backgroundColor: '#06b6d4',
                    color: 'white',
                    fontSize: '0.7rem',
                    height: '24px',
                    justifyContent: 'space-between',
                    cursor: input.protected ? 'default' : 'grab',
                    '&:active': {
                      cursor: 'grabbing',
                    },
                    '& .MuiChip-deleteIcon': { color: 'rgba(255,255,255,0.7)' }
                  }}
                />
              );
            })}
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
              sx={{ color: '#f97316', fontSize: '0.9rem', letterSpacing: '0.5px' }}
            >
              OUTPUTS ({outputs.length})
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
                {editingOutputName === output.name ? (
                  <TextField
                    autoFocus
                    size="small"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleSaveOutputEdit(output.name)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveOutputEdit(output.name);
                      } else if (e.key === 'Escape') {
                        setEditingOutputName(null);
                        setEditValue('');
                      }
                    }}
                    sx={{
                      flex: 1,
                      '& .MuiInputBase-root': {
                        height: '24px',
                        fontSize: '0.7rem',
                        backgroundColor: '#f97316',
                        color: 'white',
                      },
                      '& .MuiInputBase-input': {
                        color: 'white',
                        padding: '0 8px',
                      },
                      '& .MuiOutlinedInput-notchedOutline': {
                        border: '1px solid rgba(255,255,255,0.3)',
                      },
                    }}
                  />
                ) : (
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
                      draggable
                      onDragStart={(e) => {
                        e.stopPropagation();
                        const dragData = {
                          blockId: output.sourceBlockId || 'script_outputs',
                          outputName: output.name,
                          outputType: output.type
                        };
                        e.dataTransfer.setData('application/json', JSON.stringify(dragData));
                        e.dataTransfer.effectAllowed = 'link';
                      }}
                      onClick={(e) => {
                        // If linked and clicking on chip body (not icon), show value dialog
                        const target = e.target as HTMLElement;
                        if (!target.closest('.MuiChip-icon')) {
                          handleOutputClick(output);
                        } else if (output.sourceBlockId) {
                          // If clicking icon and linked, focus source block
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
                        cursor: 'pointer',
                        border: '2px dashed transparent',
                        '& .MuiChip-icon': { color: 'white', cursor: output.sourceBlockId ? 'pointer' : 'default' },
                        '&:hover': {
                          opacity: 0.9,
                          border: '2px dashed rgba(255,255,255,0.5)'
                        },
                        '&:active': {
                          cursor: 'grabbing',
                        }
                      }}
                    />
                  </Box>
                )}
                {editingOutputName !== output.name && (
                  <IconButton
                    size="small"
                    onClick={(e) => handleStartEditOutput(output.name, e)}
                    sx={{ padding: 0, color: '#f97316', mr: 0.5 }}
                  >
                    <EditIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                )}
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

      {/* VARIABLES Section */}
      <Box
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: 'rgba(34, 197, 94, 0.05)',
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
          onClick={() => setVariablesExpanded(!variablesExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="caption"
              fontWeight="bold"
              sx={{ color: '#22c55e', fontSize: '0.9rem', letterSpacing: '0.5px' }}
            >
              VARIABLES ({variables.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {variablesExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={variablesExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {variables.map((variable) => (
              <Box
                key={variable.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                {editingVariableName === variable.name ? (
                  <TextField
                    autoFocus
                    size="small"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleSaveVariableEdit(variable.name)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveVariableEdit(variable.name);
                      } else if (e.key === 'Escape') {
                        setEditingVariableName(null);
                        setEditValue('');
                      }
                    }}
                    sx={{
                      flex: 1,
                      '& .MuiInputBase-root': {
                        height: '24px',
                        fontSize: '0.7rem',
                        backgroundColor: '#22c55e',
                        color: 'white',
                      },
                      '& .MuiInputBase-input': {
                        color: 'white',
                        padding: '0 8px',
                      },
                      '& .MuiOutlinedInput-notchedOutline': {
                        border: '1px solid rgba(255,255,255,0.3)',
                      },
                    }}
                  />
                ) : (
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
                          
                          // Update variable with link info
                          const updatedVariables = variables.map(v => 
                            v.name === variable.name 
                              ? { 
                                  ...v, 
                                  sourceBlockId: blockId, 
                                  sourceOutputName: outputName,
                                  sourceOutputType: outputType,
                                  value: undefined // Clear static value when linked
                                }
                              : v
                          );
                          
                          // Trigger parent update
                          onUpdateVariables(updatedVariables);
                        } catch (err) {
                          console.error('Failed to parse drag data:', err);
                        }
                      }
                    }}
                  >
                    <Chip
                      icon={variable.sourceBlockId ? <LinkIcon /> : undefined}
                      label={
                        variable.sourceBlockId
                          ? `${variable.name} ← ${variable.sourceOutputName}`
                          : variable.value !== undefined
                          ? `${variable.name} = ${variable.value}`
                          : variable.name
                      }
                      size="small"
                      draggable
                      onDragStart={(e) => {
                        e.stopPropagation();
                        const dragData = {
                          blockId: variable.sourceBlockId || 'script_variables',
                          outputName: variable.name,
                          outputType: variable.type
                        };
                        e.dataTransfer.setData('application/json', JSON.stringify(dragData));
                        e.dataTransfer.effectAllowed = 'link';
                      }}
                      onClick={() => {
                        if (variable.sourceBlockId) {
                          onFocusSourceBlock(variable.sourceBlockId);
                        }
                      }}
                      sx={{
                        width: '100%',
                        backgroundColor: variable.sourceBlockId ? '#10b981' : '#22c55e',
                        color: 'white',
                        fontSize: '0.7rem',
                        height: '24px',
                        justifyContent: 'space-between',
                        cursor: variable.sourceBlockId ? 'pointer' : 'grab',
                        border: '2px dashed transparent',
                        '& .MuiChip-icon': { color: 'white' },
                        '&:active': {
                          cursor: 'grabbing',
                        }
                      }}
                    />
                  </Box>
                )}
                {editingVariableName !== variable.name && (
                  <IconButton
                    size="small"
                    onClick={(e) => handleStartEditVariable(variable.name, e)}
                    sx={{ padding: 0, color: '#22c55e', mr: 0.5 }}
                  >
                    <EditIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                )}
                <IconButton
                  size="small"
                  onClick={() => onRemoveVariable(variable.name)}
                  sx={{ padding: 0, color: '#ef4444' }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
            <Chip
              icon={<AddIcon />}
              label="Add Variable"
              size="small"
              onClick={onAddVariable}
              sx={{
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                border: '1px dashed #22c55e',
                color: '#22c55e',
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
              sx={{ color: '#a855f7', fontSize: '0.9rem', letterSpacing: '0.5px' }}
            >
              METADATA ({metadata.length})
            </Typography>
          </Box>
          <IconButton size="small">
            {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={metadataExpanded}>
          <Box sx={{ px: 2, pb: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {metadata.map((field) => (
              <Box
                key={field.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                }}
              >
                {editingMetadataField === field.name ? (
                  <TextField
                    autoFocus
                    size="small"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleSaveMetadataEdit(field.name)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveMetadataEdit(field.name);
                      } else if (e.key === 'Escape') {
                        setEditingMetadataField(null);
                        setEditValue('');
                      }
                    }}
                    sx={{
                      flex: 1,
                      '& .MuiInputBase-root': {
                        height: '24px',
                        fontSize: '0.7rem',
                        backgroundColor: '#a855f7',
                        color: 'white',
                      },
                      '& .MuiInputBase-input': {
                        color: 'white',
                        padding: '0 8px',
                      },
                      '& .MuiOutlinedInput-notchedOutline': {
                        border: '1px solid rgba(255,255,255,0.3)',
                      },
                    }}
                  />
                ) : (
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
                        backgroundColor: '#a855f7', // Always purple for metadata
                        color: 'white',
                        fontSize: '0.7rem',
                        height: '24px',
                        justifyContent: 'space-between',
                        cursor: field.sourceBlockId ? 'pointer' : 'default',
                        border: field.sourceBlockId ? '2px solid rgba(16, 185, 129, 0.6)' : '2px dashed transparent', // Green border when linked
                        '& .MuiChip-icon': { 
                          color: 'white',
                          marginLeft: '4px',
                          marginRight: '0px',
                        },
                        '& .MuiChip-label': {
                          paddingLeft: field.sourceBlockId ? '4px' : '12px',
                        },
                        '&:hover': field.sourceBlockId ? {
                          opacity: 0.9,
                          border: '2px solid rgba(16, 185, 129, 0.8)'
                        } : {}
                      }}
                    />
                  </Box>
                )}
                {editingMetadataField !== field.name && (
                  <IconButton
                    size="small"
                    onClick={(e) => handleStartEditMetadata(field.name, e)}
                    sx={{ padding: 0, color: '#a855f7', mr: 0.5 }}
                  >
                    <EditIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                )}
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
              label="Add Metadata"
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

