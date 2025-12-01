import React, { useState, useMemo, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tabs,
  Tab,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import SettingsIcon from '@mui/icons-material/Settings';
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
  const [expandedTab, setExpandedTab] = useState<string | null>(null); // Single-expand: only one tab open at a time
  const [activeMainTab, setActiveMainTab] = useState<'blocks' | 'config'>('blocks'); // Main tab: Blocks vs Config
  const reactFlowInstance = useReactFlow();
  
  // Reset expanded tab when toolbox config changes (e.g., new device selected)
  useEffect(() => {
    setExpandedTab(null);
  }, [toolboxConfig]);
  
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

  // Define tab colors (muted, professional palette)
  const tabColors: Record<string, string> = {
    'standard': '#64748b',    // slate - neutral for standard operations
    'navigation': '#7c3aed',  // violet - navigation
    'actions': '#ea580c',     // orange - actions (muted)
    'verifications': '#2563eb', // blue - verifications (muted)
    'api': '#0891b2'          // cyan - API blocks (muted)
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

  // Calculate totals for tab badges
  const totalBlocks = useMemo(() => {
    if (!toolboxConfig) return 0;
    return Object.values(toolboxConfig).reduce((total: number, tab: any) => {
      return total + (tab.groups?.reduce((sum: number, g: any) => sum + g.commands.length, 0) || 0);
    }, 0);
  }, [toolboxConfig]);

  const totalConfig = scriptInputs.length + scriptOutputs.length + scriptVariables.length + scriptMetadata.length;

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Main Tab Selector */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeMainTab}
          onChange={(_, newValue) => setActiveMainTab(newValue)}
          variant="fullWidth"
          sx={{
            minHeight: 36,
            '& .MuiTab-root': {
              minHeight: 36,
              py: 0.5,
              fontSize: 12,
              fontWeight: 500,
              textTransform: 'none',
            },
            '& .MuiTabs-indicator': {
              height: 2,
            },
          }}
        >
          <Tab 
            value="blocks" 
            icon={<ViewModuleIcon sx={{ fontSize: 16 }} />}
            iconPosition="start"
            label={`Blocks (${totalBlocks})`}
          />
          <Tab 
            value="config" 
            icon={<SettingsIcon sx={{ fontSize: 16 }} />}
            iconPosition="start"
            label={`Config (${totalConfig})`}
          />
        </Tabs>
      </Box>

      {/* BLOCKS TAB CONTENT */}
      {activeMainTab === 'blocks' && (
        <>
          {/* Search Box - Only in Blocks tab */}
          <ToolboxSearchBox
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search commands..."
          />

          {/* Block Categories - Scrollable */}
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

                  // Count total commands across all groups
                  const totalCommands = tabConfig.groups.reduce(
                    (sum: number, group: any) => sum + group.commands.length, 0
                  );
                  
                  const isExpanded = searchTerm.trim() !== '' || expandedTab === tabKey;

                  return (
                    <Accordion
                      key={tabKey}
                      expanded={isExpanded}
                      onChange={(_event, newExpanded) => {
                        setExpandedTab(newExpanded ? tabKey : null);
                      }}
                      disableGutters
                      TransitionProps={{ unmountOnExit: true }}
              sx={{
                boxShadow: 'none',
                '&:before': { display: 'none' },
                margin: '0 !important',
                borderRadius: 0,
                borderLeft: `3px solid ${tabColor}`, // Always show colored bar
                backgroundColor: isExpanded ? 'action.hover' : 'transparent',
                transition: 'all 0.15s ease',
                '& .MuiAccordionDetails-root': {
                  padding: '4px 8px 8px 12px !important',
                },
                '&.Mui-expanded': {
                  margin: '0 !important',
                }
              }}
                    >
                      <AccordionSummary
                        expandIcon={<ExpandMoreIcon sx={{ fontSize: 16, color: 'text.secondary' }} />}
                        sx={{
                          minHeight: '36px !important',
                          px: 1.5,
                          '& .MuiAccordionSummary-content': {
                            my: '8px !important',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                          },
                          '&:hover': {
                            backgroundColor: 'action.hover',
                          },
                          '&.Mui-expanded': {
                            minHeight: '36px !important',
                          }
                        }}
                      >
                        <Typography 
                          fontSize={13} 
                          fontWeight={500}
                          sx={{ 
                            color: 'text.primary',
                          }}
                        >
                          {tabName}
                        </Typography>
                        <Typography 
                          fontSize={11} 
                          sx={{ 
                            color: 'text.disabled',
                            mr: 1,
                          }}
                        >
                          {totalCommands}
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails sx={{ p: 0 }}>
                        {/* Render commands directly - flattened structure */}
                        {tabConfig.groups.map((group: any, groupIdx: number) => (
                          <React.Fragment key={`${tabKey}-group-${groupIdx}`}>
                            {/* Show group name only if multiple groups exist */}
                            {tabConfig.groups.length > 1 && (
                              <Typography 
                                fontSize={11} 
                                sx={{ 
                                  color: 'text.disabled',
                                  px: 0.5,
                                  py: 0.5,
                                  mt: groupIdx > 0 ? 1 : 0,
                                }}
                              >
                                {group.groupName}
                              </Typography>
                            )}
                            {group.commands.map((command: any, cmdIdx: number) => (
                              <DraggableCommand 
                                key={`${group.groupName}-${cmdIdx}`} 
                                command={command}
                                onCloseProgressBar={onCloseProgressBar}
                              />
                            ))}
                          </React.Fragment>
                        ))}
                      </AccordionDetails>
                    </Accordion>
                  );
                })}
              </>
            )}
          </Box>
        </>
      )}

      {/* CONFIG TAB CONTENT */}
      {activeMainTab === 'config' && (
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
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
      )}
    </Box>
  );
};

