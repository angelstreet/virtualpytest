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
  TextField,
  Collapse,
  IconButton,
  Button,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  AccountTree as TestCaseIcon,
  PlayArrow as ScriptIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material';
import { useCampaignBuilder } from '../../../contexts/campaign/CampaignBuilderContext';
import { CampaignToolboxItem, CampaignDragData } from '../../../types/pages/CampaignGraph_Types';
import { buildServerUrl } from '../../../utils/buildUrlUtils';

interface CampaignToolboxProps {
  onDragStart?: (item: CampaignToolboxItem) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  actualMode: 'light' | 'dark';
}

export const CampaignToolbox: React.FC<CampaignToolboxProps> = ({ onDragStart, isSidebarOpen, toggleSidebar, actualMode }) => {
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
  
  // Expanded sections
  const [testCasesExpanded, setTestCasesExpanded] = useState(true);
  const [scriptsExpanded, setScriptsExpanded] = useState(true);
  const [inputsExpanded, setInputsExpanded] = useState(false);
  const [outputsExpanded, setOutputsExpanded] = useState(false);
  const [reportsExpanded, setReportsExpanded] = useState(false);

  // New field inputs
  const [newInputName, setNewInputName] = useState('');
  const [newOutputName, setNewOutputName] = useState('');
  const [newReportFieldName, setNewReportFieldName] = useState('');

  // Search
  const [searchQuery, setSearchQuery] = useState('');

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

  // Add Campaign Input
  const handleAddInput = () => {
    if (!newInputName.trim()) return;
    
    addCampaignInput({
      name: newInputName.trim(),
      type: 'string',
      defaultValue: '',
    });
    setNewInputName('');
  };

  // Add Campaign Output
  const handleAddOutput = () => {
    if (!newOutputName.trim()) return;
    
    addCampaignOutput({
      name: newOutputName.trim(),
    });
    setNewOutputName('');
  };

  // Add Report Field
  const handleAddReportField = () => {
    if (!newReportFieldName.trim()) return;
    
    addCampaignReportField({
      name: newReportFieldName.trim(),
    });
    setNewReportFieldName('');
  };

  return (
    <>
      {/* Sidebar */}
      <Box
        sx={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: isSidebarOpen ? '380px' : '0px',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          borderRight: isSidebarOpen ? 1 : 0,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          background: actualMode === 'dark' ? '#0f172a' : '#f8f9fa',
          zIndex: 5,
        }}
      >
        {isSidebarOpen && (
          <>
            {/* Sidebar Header */}
            <Box
              sx={{
                px: 2,
                py: 1.5,
                height: '40px',
                borderBottom: 1,
                borderColor: 'divider',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
              }}
            >
              <Typography variant="subtitle1" fontWeight="bold">
                Toolbox
              </Typography>
              <IconButton
                size="small"
                onClick={toggleSidebar}
                sx={{
                  color: 'text.secondary',
                  '&:hover': { color: 'primary.main' },
                }}
              >
                <ChevronLeftIcon />
              </IconButton>
            </Box>
            
            {/* Search */}
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', background: actualMode === 'dark' ? '#1e293b' : '#ffffff' }}>
              <TextField
                size="small"
                fullWidth
                placeholder="Search executables..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </Box>

            {/* Scrollable Content */}
            <Box sx={{ flex: 1, overflowY: 'auto', p: 1.5 }}>
              {/* TESTCASES Category */}
              <Box sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    p: 1,
                    background: '#f3e5f5',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => setTestCasesExpanded(!testCasesExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#7b1fa2' }}>
                    TESTCASES ({filteredTestCases.length})
                  </Typography>
                  {testCasesExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Box>
                
                <Collapse in={testCasesExpanded}>
                  <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {filteredTestCases.map((item) => (
                      <Box
                        key={item.id}
                        draggable
                        onDragStart={(e) => handleToolboxItemDragStart(e, item)}
                        sx={{
                          p: 1,
                          background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                          border: '1px solid',
                          borderColor: actualMode === 'dark' ? '#334155' : '#e0e0e0',
                          borderRadius: 1,
                          cursor: 'grab',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          '&:hover': {
                            background: '#f3e5f5',
                            borderColor: '#9c27b0',
                          },
                          '&:active': {
                            cursor: 'grabbing',
                          },
                        }}
                      >
                        <TestCaseIcon sx={{ color: '#7b1fa2', fontSize: '1.2rem' }} />
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
                </Collapse>
              </Box>

              {/* SCRIPTS Category */}
              <Box sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    p: 1,
                    background: '#fff3e0',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => setScriptsExpanded(!scriptsExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#ef6c00' }}>
                    SCRIPTS ({filteredScripts.length})
                  </Typography>
                  {scriptsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Box>
                
                <Collapse in={scriptsExpanded}>
                  <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {filteredScripts.map((item) => (
                      <Box
                        key={item.id}
                        draggable
                        onDragStart={(e) => handleToolboxItemDragStart(e, item)}
                        sx={{
                          p: 1,
                          background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                          border: '1px solid',
                          borderColor: actualMode === 'dark' ? '#334155' : '#e0e0e0',
                          borderRadius: 1,
                          cursor: 'grab',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          '&:hover': {
                            background: '#fff3e0',
                            borderColor: '#ff9800',
                          },
                          '&:active': {
                            cursor: 'grabbing',
                          },
                        }}
                      >
                        <ScriptIcon sx={{ color: '#ef6c00', fontSize: '1.2rem' }} />
                        <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem' }} noWrap>
                          {item.label}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Collapse>
              </Box>

              {/* CAMPAIGN INPUTS Section */}
              <Box sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    p: 1,
                    background: '#e0f7fa',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => setInputsExpanded(!inputsExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#00838f' }}>
                    CAMPAIGN INPUTS
                  </Typography>
                  {inputsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Box>
                
                <Collapse in={inputsExpanded}>
                  <Box sx={{ mt: 0.5, p: 1, background: actualMode === 'dark' ? '#1e293b' : '#ffffff', borderRadius: 1 }}>
                    {campaignInputs.map((input) => (
                      <Box key={input.name} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                        <Chip
                          label={input.name}
                          size="small"
                          sx={{ flex: 1, background: '#b2ebf2' }}
                        />
                        <IconButton size="small" onClick={() => removeCampaignInput(input.name)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ))}
                    
                    <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                      <TextField
                        size="small"
                        placeholder="Input name"
                        value={newInputName}
                        onChange={(e) => setNewInputName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddInput()}
                        sx={{ flex: 1 }}
                      />
                      <IconButton size="small" color="primary" onClick={handleAddInput}>
                        <AddIcon />
                      </IconButton>
                    </Box>
                  </Box>
                </Collapse>
              </Box>

              {/* CAMPAIGN OUTPUTS Section */}
              <Box sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    p: 1,
                    background: '#fff3e0',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => setOutputsExpanded(!outputsExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#ef6c00' }}>
                    CAMPAIGN OUTPUTS
                  </Typography>
                  {outputsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Box>
                
                <Collapse in={outputsExpanded}>
                  <Box sx={{ mt: 0.5, p: 1, background: actualMode === 'dark' ? '#1e293b' : '#ffffff', borderRadius: 1 }}>
                    {campaignOutputs.map((output) => (
                      <Box key={output.name} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                        <Chip
                          label={output.name}
                          size="small"
                          sx={{ flex: 1, background: '#ffecb3' }}
                        />
                        <IconButton size="small" onClick={() => removeCampaignOutput(output.name)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ))}
                    
                    <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                      <TextField
                        size="small"
                        placeholder="Output name"
                        value={newOutputName}
                        onChange={(e) => setNewOutputName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddOutput()}
                        sx={{ flex: 1 }}
                      />
                      <IconButton size="small" color="primary" onClick={handleAddOutput}>
                        <AddIcon />
                      </IconButton>
                    </Box>
                  </Box>
                </Collapse>
              </Box>

              {/* CAMPAIGN REPORTS Section */}
              <Box sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    p: 1,
                    background: '#f3e5f5',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => setReportsExpanded(!reportsExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#7b1fa2' }}>
                    CAMPAIGN REPORTS
                  </Typography>
                  {reportsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Box>
                
                <Collapse in={reportsExpanded}>
                  <Box sx={{ mt: 0.5, p: 1, background: actualMode === 'dark' ? '#1e293b' : '#ffffff', borderRadius: 1 }}>
                    <FormControl size="small" fullWidth sx={{ mb: 1 }}>
                      <InputLabel>Mode</InputLabel>
                      <Select
                        value={campaignReports.mode}
                        label="Mode"
                        onChange={(e) => setCampaignReportsMode(e.target.value as 'set' | 'aggregate')}
                      >
                        <MenuItem value="set">Set (Replace)</MenuItem>
                        <MenuItem value="aggregate">Aggregate (Merge)</MenuItem>
                      </Select>
                    </FormControl>
                    
                    {campaignReports.fields.map((field) => (
                      <Box key={field.name} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                        <Chip
                          label={field.name}
                          size="small"
                          sx={{ flex: 1, background: '#e1bee7' }}
                        />
                        <IconButton size="small" onClick={() => removeCampaignReportField(field.name)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ))}
                    
                    <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                      <TextField
                        size="small"
                        placeholder="Report field"
                        value={newReportFieldName}
                        onChange={(e) => setNewReportFieldName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddReportField()}
                        sx={{ flex: 1 }}
                      />
                      <IconButton size="small" color="primary" onClick={handleAddReportField}>
                        <AddIcon />
                      </IconButton>
                    </Box>
                  </Box>
                </Collapse>
              </Box>
            </Box>
          </>
        )}
      </Box>
      
      {/* Toggle Button (when sidebar is closed) */}
      {!isSidebarOpen && (
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: '140px',
            zIndex: 10,
          }}
        >
          <IconButton
            onClick={toggleSidebar}
            sx={{
              background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
              border: 1,
              borderColor: 'divider',
              borderRadius: '0 8px 8px 0',
              '&:hover': {
                background: actualMode === 'dark' ? '#334155' : '#f1f5f9',
              },
            }}
          >
            <ExpandMoreIcon sx={{ transform: 'rotate(-90deg)' }} />
          </IconButton>
        </Box>
      )}
    </>
  );
};

