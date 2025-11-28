import React, { useState, useMemo, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { ScriptIOSections } from './ScriptIOSections';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';
import { useReactFlow } from 'reactflow';
import { ToolboxSearchBox } from '../../common/builder/ToolboxSearchBox';
import { DraggableCommand } from '../../common/builder/DraggableCommand';

interface TestCaseToolboxProps {
  toolboxConfig: any;  // Dynamic config from backend
  onCloseProgressBar?: () => void;
  // Take control data for initializing default inputs
  selectedHost?: any;
  selectedDeviceId?: string | null;
  userinterfaceName?: string;
}

export const TestCaseToolbox: React.FC<TestCaseToolboxProps> = ({ 
  toolboxConfig,  // No fallback - must provide dynamic config
  onCloseProgressBar,
  selectedHost,
  selectedDeviceId,
  userinterfaceName: userinterface
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const reactFlowInstance = useReactFlow();
  
  // Access Script I/O state from context
  const {
    scriptInputs,
    setScriptInputs,
    scriptOutputs,
    setScriptOutputs,
    scriptVariables,
    setScriptVariables,
    scriptMetadata,
    setScriptMetadata,
  } = useTestCaseBuilder();

  // Initialize default inputs from take control data
  // These 4 inputs are protected and cannot be deleted
  // This also runs after script load to restore protected inputs
  useEffect(() => {
    // Get current values
    const hostName = selectedHost?.host_name || '';
    const deviceName = selectedDeviceId || '';
    const userinterfaceName = userinterface || '';
    const selectedDevice = selectedHost?.devices?.find((d: any) => d.device_id === selectedDeviceId);
    const deviceModelName = selectedDevice?.device_model || '';

    // Check if default inputs already exist
    const hasHostInput = scriptInputs.some(input => input.name === 'host_name');
    const hasDeviceInput = scriptInputs.some(input => input.name === 'device_name');
    const hasUserinterfaceInput = scriptInputs.some(input => input.name === 'userinterface_name');
    const hasDeviceModelInput = scriptInputs.some(input => input.name === 'device_model_name');

    // Initialize default inputs if they don't exist
    const defaultInputs = [];
    
    if (!hasHostInput) {
      defaultInputs.push({
        name: 'host_name',
        type: 'string',
        required: true,
        protected: true,
        default: hostName,
      });
    }
    
    if (!hasDeviceInput) {
      defaultInputs.push({
        name: 'device_name',
        type: 'string',
        required: true,
        protected: true,
        default: deviceName,
      });
    }
    
    if (!hasDeviceModelInput) {
      defaultInputs.push({
        name: 'device_model_name',
        type: 'string',
        required: true,
        protected: true,
        default: deviceModelName,
      });
    }
    
    if (!hasUserinterfaceInput) {
      defaultInputs.push({
        name: 'userinterface_name',
        type: 'string',
        required: true,
        protected: true,
        default: userinterfaceName,
      });
    }

    // Add default inputs if any are missing (prepend them to the beginning)
    if (defaultInputs.length > 0) {
      setScriptInputs([...defaultInputs, ...scriptInputs]);
    } else {
      // Update default values if inputs already exist
      const updatedInputs = scriptInputs.map(input => {
        if (input.name === 'host_name' && input.protected) {
          return { ...input, default: hostName };
        }
        if (input.name === 'device_name' && input.protected) {
          return { ...input, default: deviceName };
        }
        if (input.name === 'userinterface_name' && input.protected) {
          return { ...input, default: userinterfaceName };
        }
        if (input.name === 'device_model_name' && input.protected) {
          return { ...input, default: deviceModelName };
        }
        return input;
      });
      
      // Only update if values changed
      const hasChanged = updatedInputs.some((input, idx) => 
        input.default !== scriptInputs[idx].default
      );
      
      if (hasChanged) {
        setScriptInputs(updatedInputs);
      }
    }
  }, [selectedHost, selectedDeviceId, userinterface, scriptInputs.length]); // Trigger when inputs count changes (e.g., after load)

  // Define tab colors (matching block type colors)
  const tabColors: Record<string, string> = {
    'standard': '#6b7280',    // grey - neutral for standard operations
    'navigation': '#8b5cf6',  // purple - unchanged
    'actions': '#f97316',     // orange - distinguishable from failure (red)
    'verifications': '#3b82f6', // blue - distinguishable from success (green)
    'api': '#06b6d4'          // cyan - API blocks
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
  
  const handleAddVariable = () => {
    const newVariable = {
      name: `var_${scriptVariables.length + 1}`,
      type: 'string',
    };
    setScriptVariables([...scriptVariables, newVariable]);
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
  
  const handleRemoveVariable = (name: string) => {
    setScriptVariables(scriptVariables.filter((variable: any) => variable.name !== name));
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
      {/* Filter/Search Box - Using shared component */}
      <ToolboxSearchBox
        value={searchTerm}
        onChange={setSearchTerm}
        placeholder="Search commands..."
      />

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
        variables={scriptVariables}
        metadata={scriptMetadata}
        onAddInput={handleAddInput}
        onAddOutput={handleAddOutput}
        onAddVariable={handleAddVariable}
        onAddMetadataField={handleAddMetadataField}
        onRemoveInput={handleRemoveInput}
        onRemoveOutput={handleRemoveOutput}
        onRemoveVariable={handleRemoveVariable}
        onRemoveMetadataField={handleRemoveMetadataField}
        onFocusSourceBlock={handleFocusSourceBlock}
        onUpdateOutputs={setScriptOutputs}
        onUpdateVariables={setScriptVariables}
        onUpdateMetadata={setScriptMetadata}
      />
    </Box>
  );
};

