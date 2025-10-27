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
import { UnifiedExecutableSelector, ExecutableItem } from '../common/UnifiedExecutableSelector';

interface ScriptSequenceBuilderProps {
  scripts: ScriptConfiguration[];
  availableScripts: string[];
  aiTestCasesInfo?: any[];
  scriptAnalysisCache: { [scriptName: string]: any };
  deviceModel?: string; // Device model for userinterface selection
  userinterfaceName?: string; // For edge selector (kpi_measurement)
  hostName?: string; // For edge selector (kpi_measurement)
  onAddScript: (scriptName: string) => void;
  onRemoveScript: (index: number) => void;

  onUpdateScript: (index: number, updates: Partial<ScriptConfiguration>) => void;
  onLoadScriptAnalysis: (scriptName: string) => Promise<any>;
}

export const ScriptSequenceBuilder: React.FC<ScriptSequenceBuilderProps> = ({
  scripts,
  aiTestCasesInfo = [],
  scriptAnalysisCache,
  deviceModel,
  userinterfaceName,
  hostName,
  onAddScript,
  onRemoveScript,

  onUpdateScript,
  onLoadScriptAnalysis,
}) => {
  const [addScriptDialogOpen, setAddScriptDialogOpen] = useState(false);
  const [selectedExecutableToAdd, setSelectedExecutableToAdd] = useState<ExecutableItem | null>(null);
  const [expandedScript, setExpandedScript] = useState<string | false>(false);

  const handleAddScript = () => {
    if (selectedExecutableToAdd) {
      onAddScript(selectedExecutableToAdd.id); // Use the executable ID (script filename or testcase UUID)
      setSelectedExecutableToAdd(null);
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

    // Framework parameters are configured at campaign level, not per-script
    // Filter them out to avoid duplicate UI (host/device/userinterface already set for whole campaign)
    const FRAMEWORK_PARAMS = ['host', 'device', 'userinterface_name'];
    
    const displayParameters = analysis.parameters.filter((param: any) => 
      // Show all parameters EXCEPT framework ones (which are set at campaign level)
      !FRAMEWORK_PARAMS.includes(param.name)
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
            userinterfaceName={userinterfaceName}
            hostName={hostName}
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
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Add Script or Test Case to Campaign</DialogTitle>
        <DialogContent sx={{ minHeight: 400 }}>
          <UnifiedExecutableSelector
            value={selectedExecutableToAdd}
            onChange={setSelectedExecutableToAdd}
            label="Select Script or Test Case"
            placeholder="Search by name..."
            filters={{ folders: true, tags: true, search: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddScriptDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleAddScript} 
            variant="contained"
            disabled={!selectedExecutableToAdd}
          >
            Add to Campaign
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
