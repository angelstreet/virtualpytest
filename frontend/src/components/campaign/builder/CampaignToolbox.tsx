/**
 * Campaign Toolbox Component
 * 
 * Left sidebar toolbox for the campaign builder.
 * Contains:
 * - Draggable executable items (TestCases, Scripts)
 * - Campaign I/O sections (Inputs, Outputs, Reports)
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  AccountTree as TestCaseIcon,
  PlayArrow as ScriptIcon,
} from '@mui/icons-material';
import { useCampaignBuilder } from '../../../contexts/campaign/CampaignBuilderContext';
import { CampaignToolboxItem, CampaignDragData } from '../../../types/pages/CampaignGraph_Types';
import { buildServerUrl } from '../../../utils/buildUrlUtils';
import { ScriptIOSections } from '../../testcase/builder/ScriptIOSections';
import { ToolboxSearchBox } from '../../common/builder/ToolboxSearchBox';
import { toolboxConfig as sharedToolboxConfig } from '../../testcase/builder/toolboxConfig';
import { DraggableCommand } from '../../common/builder/DraggableCommand';

interface CampaignToolboxProps {
  onDragStart?: (item: CampaignToolboxItem) => void;
}

export const CampaignToolbox: React.FC<CampaignToolboxProps> = ({ onDragStart }) => {
  const {
    campaignInputs,
    campaignOutputs,
    campaignReports,
    addCampaignInput,
    addCampaignOutput,
    addCampaignReportField,
    removeCampaignInput,
    removeCampaignOutput,
    removeCampaignReportField,
    setCampaignReportsMode,
  } = useCampaignBuilder();

  // Toolbox items
  const [testCases, setTestCases] = useState<CampaignToolboxItem[]>([]);
  const [scripts, setScripts] = useState<CampaignToolboxItem[]>([]);
  
  // Search
  const [searchQuery, setSearchQuery] = useState('');

  // Category colors - matching TestCase Builder style
  const categoryColors = {
    standard: '#6b7280',  // Grey - for STANDARD commands (shared with TestCase)
    testcases: '#9c27b0', // Purple - matching testcase blocks
    scripts: '#ff9800',   // Orange - matching script blocks
  };

  // Get STANDARD commands from shared toolbox config
  const standardCommands = sharedToolboxConfig.standard;

  // Load available executables
  useEffect(() => {
    loadTestCases();
    loadScripts();
  }, []);

  const loadTestCases = async () => {
    try {
      const apiUrl = buildServerUrl('/api/testcases');
      const response = await fetch(apiUrl);
      if (!response.ok) return;
      
      const data = await response.json();
      const items: CampaignToolboxItem[] = data.testcases.map((tc: any) => ({
        id: tc.id,
        type: 'testcase' as const,
        label: tc.name,
        icon: '🌳',
        category: 'testcases' as const,
        executableId: tc.id,
        executableType: 'testcase' as const,
        executableName: tc.name,
        description: tc.description,
        tags: tc.tags,
        folder: tc.folder,
      }));
      
      setTestCases(items);
    } catch (error) {
      console.error('[@CampaignToolbox] Error loading testcases:', error);
    }
  };

  const loadScripts = async () => {
    try {
      const apiUrl = buildServerUrl('/api/test-scripts/available');
      const response = await fetch(apiUrl);
      if (!response.ok) return;
      
      const data = await response.json();
      const items: CampaignToolboxItem[] = (data.scripts || []).map((scriptName: string) => ({
        id: scriptName,
        type: 'script' as const,
        label: scriptName,
        icon: '▶️',
        category: 'scripts' as const,
        executableId: scriptName,
        executableType: 'script' as const,
        executableName: scriptName,
      }));
      
      setScripts(items);
    } catch (error) {
      console.error('[@CampaignToolbox] Error loading scripts:', error);
    }
  };

  // Handle drag start for toolbox items
  const handleToolboxItemDragStart = (e: React.DragEvent, item: CampaignToolboxItem) => {
    const dragData: CampaignDragData = {
      type: 'toolbox-item',
      toolboxItem: item,
    };
    e.dataTransfer.setData('application/json', JSON.stringify(dragData));
    e.dataTransfer.effectAllowed = 'copy';
    
    if (onDragStart) {
      onDragStart(item);
    }
  };

  // Filter items by search
  const filterItems = (items: CampaignToolboxItem[]) => {
    if (!searchQuery) return items;
    const query = searchQuery.toLowerCase();
    return items.filter(item =>
      item.label.toLowerCase().includes(query) ||
      item.description?.toLowerCase().includes(query)
    );
  };

  const filteredTestCases = filterItems(testCases);
  const filteredScripts = filterItems(scripts);

  // Transform campaign data to match ScriptIOSections interface
  const inputs = campaignInputs.map(input => ({
    name: input.name,
    type: input.type || 'string',
    required: false,
    default: input.defaultValue,
  }));

  const outputs = campaignOutputs.map(output => ({
    name: output.name,
    type: 'string',
  }));

  const metadata = campaignReports.fields.map(field => ({
    name: field.name,
    value: undefined,
  }));

  // I/O Section handlers
  const handleAddInput = () => {
    const name = prompt('Enter input name:');
    if (name && name.trim()) {
      addCampaignInput({
        name: name.trim(),
        type: 'string',
        defaultValue: '',
      });
    }
  };

  const handleAddOutput = () => {
    const name = prompt('Enter output name:');
    if (name && name.trim()) {
      addCampaignOutput({
        name: name.trim(),
      });
    }
  };

  const handleAddMetadata = () => {
    const name = prompt('Enter report field name:');
    if (name && name.trim()) {
      addCampaignReportField({
        name: name.trim(),
      });
    }
  };

  const handleRemoveInput = (name: string) => {
    removeCampaignInput(name);
  };

  const handleRemoveOutput = (name: string) => {
    removeCampaignOutput(name);
  };

  const handleRemoveMetadata = (name: string) => {
    removeCampaignReportField(name);
  };

  const handleFocusSourceBlock = (blockId: string) => {
    console.log('[@CampaignToolbox] Focus source block:', blockId);
    // TODO: Implement focus/zoom to block
  };

  const handleUpdateOutputs = (updatedOutputs: any[]) => {
    console.log('[@CampaignToolbox] Update outputs:', updatedOutputs);
    // TODO: Update campaign outputs with linked data
  };

  const handleUpdateMetadata = (updatedMetadata: any[]) => {
    console.log('[@CampaignToolbox] Update metadata:', updatedMetadata);
    // TODO: Update campaign report fields with linked data
  };

  return (
    <>
      {/* Search - Using shared component */}
      <ToolboxSearchBox
        value={searchQuery}
        onChange={setSearchQuery}
        placeholder="Search executables..."
      />

      {/* Scrollable Content - Using Accordion like TestCase Builder */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 0.5,
        }}
      >
        {/* STANDARD Category - Shared with TestCase Builder */}
        <Accordion
          defaultExpanded={searchQuery.trim() !== ''}
          sx={{
            boxShadow: 'none',
            '&:before': { display: 'none'},
            padding: '2px !important',
            margin: '4px !important',
            mb: 1,
            borderLeft: `4px solid ${categoryColors.standard}`,
            backgroundColor: `${categoryColors.standard}08`,
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
            expandIcon={<ExpandMoreIcon sx={{ fontSize: 18, color: categoryColors.standard }} />}
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
                color: categoryColors.standard,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}
            >
              STANDARD
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 1 }}>
            {/* Render each group with nested accordion */}
            {standardCommands.groups.map((group: any, groupIdx: number) => (
              <Accordion
                key={`standard-group-${groupIdx}`}
                defaultExpanded={true}
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
                    />
                  ))}
                </AccordionDetails>
              </Accordion>
            ))}
          </AccordionDetails>
        </Accordion>

        {/* TESTCASES Category - Exact same style as TestCase Builder tabs */}
        <Accordion
          defaultExpanded={searchQuery.trim() !== ''}
          sx={{
            boxShadow: 'none',
            '&:before': { display: 'none'},
            padding: '2px !important',
            margin: '4px !important',
            mb: 1,
            borderLeft: `4px solid ${categoryColors.testcases}`,
            backgroundColor: `${categoryColors.testcases}08`,
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
            expandIcon={<ExpandMoreIcon sx={{ fontSize: 18, color: categoryColors.testcases }} />}
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
                color: categoryColors.testcases,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}
            >
              TESTCASES ({filteredTestCases.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 1 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {filteredTestCases.map((item) => (
                <Box
                  key={item.id}
                  draggable
                  onDragStart={(e) => handleToolboxItemDragStart(e, item)}
                  sx={{
                    p: 1,
                    background: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    cursor: 'grab',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    '&:hover': {
                      background: `${categoryColors.testcases}15`,
                      borderColor: categoryColors.testcases,
                    },
                    '&:active': {
                      cursor: 'grabbing',
                    },
                  }}
                >
                  <TestCaseIcon sx={{ color: categoryColors.testcases, fontSize: '1.2rem' }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', fontSize: '0.75rem' }} noWrap>
                      {item.label}
                    </Typography>
                    {item.folder && (
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }} noWrap>
                        {item.folder}
                      </Typography>
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* SCRIPTS Category - Exact same style as TestCase Builder tabs */}
        <Accordion
          defaultExpanded={searchQuery.trim() !== ''}
          sx={{
            boxShadow: 'none',
            '&:before': { display: 'none'},
            padding: '2px !important',
            margin: '4px !important',
            mb: 1,
            borderLeft: `4px solid ${categoryColors.scripts}`,
            backgroundColor: `${categoryColors.scripts}08`,
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
            expandIcon={<ExpandMoreIcon sx={{ fontSize: 18, color: categoryColors.scripts }} />}
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
                color: categoryColors.scripts,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}
            >
              SCRIPTS ({filteredScripts.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 1 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {filteredScripts.map((item) => (
                <Box
                  key={item.id}
                  draggable
                  onDragStart={(e) => handleToolboxItemDragStart(e, item)}
                  sx={{
                    p: 1,
                    background: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    cursor: 'grab',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    '&:hover': {
                      background: `${categoryColors.scripts}15`,
                      borderColor: categoryColors.scripts,
                    },
                    '&:active': {
                      cursor: 'grabbing',
                    },
                  }}
                >
                  <ScriptIcon sx={{ color: categoryColors.scripts, fontSize: '1.2rem' }} />
                  <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem' }} noWrap>
                    {item.label}
                  </Typography>
                </Box>
              ))}
            </Box>
          </AccordionDetails>
        </Accordion>
      </Box>

      {/* I/O Sections - Reusing TestCase component for consistent styling */}
      <ScriptIOSections
        inputs={inputs}
        outputs={outputs}
        metadata={metadata}
        onAddInput={handleAddInput}
        onAddOutput={handleAddOutput}
        onAddMetadataField={handleAddMetadata}
        onRemoveInput={handleRemoveInput}
        onRemoveOutput={handleRemoveOutput}
        onRemoveMetadataField={handleRemoveMetadata}
        onFocusSourceBlock={handleFocusSourceBlock}
        onUpdateOutputs={handleUpdateOutputs}
        onUpdateMetadata={handleUpdateMetadata}
      />
    </>
  );
};

