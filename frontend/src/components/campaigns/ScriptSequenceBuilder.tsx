/**
 * Script Sequence Builder Component
 * 
 * Component for building and managing the sequence of scripts in a campaign.
 * Supports adding, removing, reordering, and configuring scripts.
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  DragIndicator as DragIcon,
  ExpandMore as ExpandMoreIcon,

  PlayArrow as ScriptIcon,
} from '@mui/icons-material';
import { ScriptConfiguration } from '../../types/pages/Campaign_Types';
import { ParameterInputRenderer } from '../common/ParameterInput/ParameterInputRenderer';
import { getScriptDisplayName, isAIScript } from '../../utils/executionUtils';

interface ScriptSequenceBuilderProps {
  scripts: ScriptConfiguration[];
  availableScripts: string[];
  aiTestCasesInfo?: any[];
  scriptAnalysisCache: { [scriptName: string]: any };
  deviceModel?: string; // Device model for userinterface selection
  onAddScript: (scriptName: string) => void;
  onRemoveScript: (index: number) => void;

  onUpdateScript: (index: number, updates: Partial<ScriptConfiguration>) => void;
  onLoadScriptAnalysis: (scriptName: string) => Promise<any>;
}

export const ScriptSequenceBuilder: React.FC<ScriptSequenceBuilderProps> = ({
  scripts,
  availableScripts,
  aiTestCasesInfo = [],
  scriptAnalysisCache,
  deviceModel,
  onAddScript,
  onRemoveScript,

  onUpdateScript,
  onLoadScriptAnalysis,
}) => {
  const [addScriptDialogOpen, setAddScriptDialogOpen] = useState(false);
  const [selectedScriptToAdd, setSelectedScriptToAdd] = useState('');
  const [expandedScript, setExpandedScript] = useState<string | false>(false);

  const handleAddScript = () => {
    if (selectedScriptToAdd) {
      onAddScript(selectedScriptToAdd);
      setSelectedScriptToAdd('');
      setAddScriptDialogOpen(false);
    }
  };

  const handleScriptParameterChange = (scriptIndex: number, paramName: string, value: string) => {
    const currentScript = scripts[scriptIndex];
    const updatedParameters = {
      ...currentScript.parameters,
      [paramName]: value,
    };
    
    onUpdateScript(scriptIndex, { parameters: updatedParameters });
  };

  const handleAccordionChange = (scriptId: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedScript(isExpanded ? scriptId : false);
    
    // Load script analysis when expanding
    if (isExpanded) {
      const script = scripts.find(s => `${s.script_name}-${s.order}` === scriptId);
      if (script && !scriptAnalysisCache[script.script_name]) {
        onLoadScriptAnalysis(script.script_name);
      }
    }
  };

  const renderScriptParameters = (script: ScriptConfiguration, scriptIndex: number) => {
    const analysis = scriptAnalysisCache[script.script_name];
    if (!analysis || !analysis.parameters) {
      return (
        <Typography variant="body2" color="text.secondary">
          No parameters available for this script
        </Typography>
      );
    }

    // Filter parameters to show only required ones and important optional ones
    // Exclude framework parameters: host, device, userinterface_name (shown at campaign level)
    const displayParameters = analysis.parameters.filter((param: any) => 
      (param.required && param.name !== 'host' && param.name !== 'device' && param.name !== 'userinterface_name') ||
      param.name === 'blackscreen_area' ||
      param.name === 'node'
    );

    if (displayParameters.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary">
          No configurable parameters for this script
        </Typography>
      );
    }

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {displayParameters.map((param: any) => (
          <ParameterInputRenderer
            key={param.name}
            parameter={param}
            value={script.parameters[param.name] || param.default || ''}
            onChange={(name: string, value: any) => handleScriptParameterChange(scriptIndex, name, value)}
            error={param.required && !script.parameters[param.name]}
            deviceModel={deviceModel}
          />
        ))}
      </Box>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Script Sequence ({scripts.length} scripts)
        </Typography>
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => setAddScriptDialogOpen(true)}
          size="small"
        >
          Add Script
        </Button>
      </Box>

      {/* Script List */}
      {scripts.length === 0 ? (
        <Card variant="outlined">
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body2" color="text.secondary">
              No scripts added yet. Click "Add Script" to get started.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {scripts.map((script, index) => {
            const scriptId = `${script.script_name}-${script.order}`;
            // Analysis cached for future use
            scriptAnalysisCache[script.script_name];
            
            return (
              <Accordion
                key={scriptId}
                expanded={expandedScript === scriptId}
                onChange={handleAccordionChange(scriptId)}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', mr: 2 }}>
                    <DragIcon sx={{ color: 'text.secondary' }} />
                    
                    <Chip
                      label={`${index + 1}`}
                      size="small"
                      color="primary"
                      sx={{ minWidth: 32 }}
                    />
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                      <ScriptIcon sx={{ color: 'text.secondary' }} />
                      <Typography variant="body1">
                        {getScriptDisplayName(script.script_name, aiTestCasesInfo)}
                      </Typography>
                      {isAIScript(script.script_name) && (
                        <Chip label="AI" size="small" color="primary" />
                      )}
                    </Box>
                    
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveScript(index);
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </AccordionSummary>
                
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Script Description */}
                    <TextField
                      label="Description"
                      value={script.description || ''}
                      onChange={(e) => onUpdateScript(index, { description: e.target.value })}
                      size="small"
                      fullWidth
                      multiline
                      rows={2}
                      placeholder="Optional description for this script execution..."
                    />
                    
                    {/* Script Parameters */}
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Parameters
                      </Typography>
                      {renderScriptParameters(script, index)}
                    </Box>
                  </Box>
                </AccordionDetails>
              </Accordion>
            );
          })}
        </Box>
      )}

      {/* Add Script Dialog */}
      <Dialog
        open={addScriptDialogOpen}
        onClose={() => setAddScriptDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Script to Campaign</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Select Script</InputLabel>
            <Select
              value={selectedScriptToAdd}
              label="Select Script"
              onChange={(e) => setSelectedScriptToAdd(e.target.value)}
            >
              {availableScripts.map((scriptName) => (
                <MenuItem key={scriptName} value={scriptName}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {isAIScript(scriptName) && (
                      <Chip 
                        label="AI" 
                        size="small" 
                        color="primary" 
                        sx={{ fontSize: '0.7rem', height: '18px' }} 
                      />
                    )}
                    <Typography variant="body2">
                      {getScriptDisplayName(scriptName, aiTestCasesInfo)}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddScriptDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleAddScript} 
            variant="contained"
            disabled={!selectedScriptToAdd}
          >
            Add Script
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
