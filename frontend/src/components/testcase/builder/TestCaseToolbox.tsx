import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  InputAdornment,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import { toolboxConfig as staticToolboxConfig, CommandConfig } from './toolboxConfig';
import { ScriptIOSections } from './ScriptIOSections';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';
import { useReactFlow } from 'reactflow';

interface DraggableCommandProps {
  command: CommandConfig;
  onCloseProgressBar?: () => void;
}

const DraggableCommand: React.FC<DraggableCommandProps> = ({ command, onCloseProgressBar }) => {
  const onDragStart = (event: React.DragEvent) => {
    // Close progress bar when starting to drag a command
    onCloseProgressBar?.();
    
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
        py: 0.5,
        px: 0.5,
        mb: 0.5,
        cursor: 'grab',
        display: 'flex',
        alignItems: 'center',
        lineHeight: 1.5,
        minHeight: '0 !important',
        height: 'auto',
        '&:hover': {
          boxShadow: 1,
          transform: 'translateX(12px)',
        },
        '&:active': {
          cursor: 'grabbing',
        },
        transition: 'all 0.15s',
        borderLeft: `3px solid ${command.color}`,
      }}
      title={command.description}
    >
      <Typography fontSize={13} noWrap sx={{ lineHeight: 1, mb: 0 }}>
        {command.label}
      </Typography>
    </Paper>
  );
};

interface TestCaseToolboxProps {
  toolboxConfig?: any;  // Optional dynamic config
  onCloseProgressBar?: () => void;
}

export const TestCaseToolbox: React.FC<TestCaseToolboxProps> = ({ 
  toolboxConfig = staticToolboxConfig,  // Fallback to static config
  onCloseProgressBar
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const reactFlowInstance = useReactFlow();
  
  // Access Script I/O state from context
  const {
    scriptInputs,
    setScriptInputs,
    scriptOutputs,
    setScriptOutputs,
    scriptMetadata,
    setScriptMetadata,
    metadataMode,
    setMetadataMode,
  } = useTestCaseBuilder();

  // Define tab colors (matching block type colors)
  const tabColors: Record<string, string> = {
    'standard': '#6b7280',    // grey - neutral for standard operations
    'navigation': '#8b5cf6',  // purple - unchanged
    'actions': '#f97316',     // orange - distinguishable from failure (red)
    'verifications': '#3b82f6' // blue - distinguishable from success (green)
  };

  // Handle null/undefined toolboxConfig (should be rare since parent handles it)
  if (!toolboxConfig || typeof toolboxConfig !== 'object') {
    return null;
  }

  // Filter toolbox config based on search term
  const filteredToolboxConfig = useMemo(() => {
    if (!searchTerm.trim()) {
      return toolboxConfig;
    }

    const searchLower = searchTerm.toLowerCase().trim();
    const filtered: any = {};

    Object.keys(toolboxConfig).forEach((tabKey) => {
      const tabConfig = toolboxConfig[tabKey];
      const filteredGroups = tabConfig.groups
        .map((group: any) => ({
          ...group,
          commands: group.commands.filter((command: any) => 
            (command.label || '').toLowerCase().includes(searchLower) ||
            (command.description || '').toLowerCase().includes(searchLower) ||
            (command.type || '').toLowerCase().includes(searchLower)
          )
        }))
        .filter((group: any) => group.commands.length > 0);

      if (filteredGroups.length > 0) {
        filtered[tabKey] = {
          ...tabConfig,
          groups: filteredGroups
        };
      }
    });

    return filtered;
  }, [toolboxConfig, searchTerm]);
  
  // I/O Section Handlers
  const handleAddInput = () => {
    const newInput = {
      name: `input_${scriptInputs.length + 1}`,
      type: 'string',
      required: false,
    };
    setScriptInputs([...scriptInputs, newInput]);
  };
  
  const handleAddOutput = () => {
    const newOutput = {
      name: `output_${scriptOutputs.length + 1}`,
      type: 'string',
    };
    setScriptOutputs([...scriptOutputs, newOutput]);
  };
  
  const handleAddMetadataField = () => {
    const newField = {
      name: `field_${scriptMetadata.length + 1}`,
    };
    setScriptMetadata([...scriptMetadata, newField]);
  };
  
  const handleRemoveInput = (name: string) => {
    setScriptInputs(scriptInputs.filter(input => input.name !== name));
  };
  
  const handleRemoveOutput = (name: string) => {
    setScriptOutputs(scriptOutputs.filter(output => output.name !== name));
  };
  
  const handleRemoveMetadataField = (name: string) => {
    setScriptMetadata(scriptMetadata.filter(field => field.name !== name));
  };
  
  const handleFocusSourceBlock = (blockId: string) => {
    const node = reactFlowInstance?.getNode(blockId);
    if (node && reactFlowInstance) {
      reactFlowInstance.setCenter(node.position.x + 100, node.position.y + 50, { zoom: 1.5, duration: 800 });
    }
  };

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Filter/Search Box */}
      <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Search commands..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchTerm && (
              <InputAdornment position="end">
                <IconButton
                  size="small"
                  onClick={() => setSearchTerm('')}
                  edge="end"
                >
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
            sx: { fontSize: '0.875rem' }
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              '&:hover fieldset': {
                borderColor: 'primary.main',
              },
            },
          }}
        />
      </Box>

      {/* All Tabs - Scrollable */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 0.5,
        }}
      >
        {/* Show message if no results */}
        {Object.keys(filteredToolboxConfig).length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              No commands found for "{searchTerm}"
            </Typography>
          </Box>
        ) : (
          <>
            {/* Iterate through filtered tabs */}
            {Object.keys(filteredToolboxConfig).map((tabKey) => {
              const tabConfig = filteredToolboxConfig[tabKey];
              const tabColor = tabColors[tabKey] || '#6b7280';
              const tabName = tabConfig.tabName || tabKey;

          return (
            <Accordion
              key={tabKey}
              defaultExpanded={searchTerm.trim() !== ''} // Auto-expand when searching
              sx={{
                boxShadow: 'none',
                '&:before': { display: 'none'},
                padding: '2px !important',
                margin: '4px !important',
                mb: 1,
                borderLeft: `4px solid ${tabColor}`,
                backgroundColor: `${tabColor}08`, // Very subtle background tint
                '& .MuiAccordionDetails-root': {
                  padding: '8px !important',
                  margin: '0px !important',
                },
                '&.Mui-expanded': {
                  padding: '2px !important',
                  margin: '4px !important',
                  minHeight: '0 !important',
                }
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon sx={{ fontSize: 18, color: tabColor }} />}
                sx={{
                  minHeight: '28px !important',
                  height: '28px',
                  py: '20px !important',
                  px: 1,
                  '& .MuiAccordionSummary-content': {
                    my: '0 !important',
                    minHeight: '28px !important',
                    py: '20px !important',
                  },
                  '&.Mui-expanded': {
                    minHeight: '28px !important',
                    height: '28px',
                    my: '0 !important',
                    py: '20px !important',
                  }
                }}
              >
                <Typography 
                  fontSize={14} 
                  fontWeight="bold" 
                  sx={{ 
                    color: tabColor,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}
                >
                  {tabName}
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 1 }}>
                {/* Render each group with collapsible header */}
                {tabConfig.groups.map((group: any, groupIdx: number) => (
                  <Accordion
                    key={`${tabKey}-group-${groupIdx}`}
                    defaultExpanded={true} // Always expanded
                    sx={{
                      boxShadow: 'none',
                      '&:before': { display: 'none'},
                      margin: '0 !important',
                      marginBottom: '2px !important',
                      padding: '0 !important',
                      backgroundColor: 'transparent',
                      '&.Mui-expanded': {
                        margin: '0 !important',
                        marginBottom: '2px !important',
                        minHeight: '0 !important',
                      }
                    }}
                  >
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon sx={{ fontSize: 14 }} />}
                      sx={{
                        minHeight: '20px !important',
                        height: '20px',
                        padding: '0 4px !important',
                        margin: '0 !important',
                        '& .MuiAccordionSummary-content': {
                          margin: '0 !important',
                          minHeight: '20px !important',
                        },
                        '&.Mui-expanded': {
                          minHeight: '20px !important',
                          height: '20px',
                          margin: '0 !important',
                        }
                      }}
                    >
                      <Typography 
                        fontSize={12} 
                        fontWeight="bold" 
                        padding={0.5}
                        sx={{ 
                          color: 'text.secondary',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          opacity: 0.8
                        }}
                      >
                        {group.groupName} ({group.commands.length})
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails sx={{ padding: '0 !important', margin: '0 !important' }}>
                      {group.commands.map((command: any, cmdIdx: number) => (
                        <DraggableCommand 
                          key={`${group.groupName}-${cmdIdx}`} 
                          command={command}
                          onCloseProgressBar={onCloseProgressBar}
                        />
                      ))}
                    </AccordionDetails>
                  </Accordion>
                ))}
              </AccordionDetails>
            </Accordion>
          );
        })}
          </>
        )}
      </Box>

      {/* Script I/O Sections (Fixed at bottom) */}
      <ScriptIOSections
        inputs={scriptInputs}
        outputs={scriptOutputs}
        metadata={scriptMetadata}
        metadataMode={metadataMode}
        onAddInput={handleAddInput}
        onAddOutput={handleAddOutput}
        onAddMetadataField={handleAddMetadataField}
        onRemoveInput={handleRemoveInput}
        onRemoveOutput={handleRemoveOutput}
        onRemoveMetadataField={handleRemoveMetadataField}
        onMetadataModeChange={setMetadataMode}
        onFocusSourceBlock={handleFocusSourceBlock}
        onUpdateOutputs={setScriptOutputs}
        onUpdateMetadata={setScriptMetadata}
      />
    </Box>
  );
};

