/**
 * Run Campaigns Page
 * 
 * Main interface for creating, configuring, and executing test campaigns.
 * Features campaign builder, execution monitoring, and campaign history.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import {
  PlayArrow as LaunchIcon,
  Timeline as HistoryIcon,
  Link as LinkIcon,
} from '@mui/icons-material';

import { useCampaign } from '../hooks/pages/useCampaign';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { CampaignConfigForm } from '../components/campaigns/CampaignConfigForm';
import { ScriptSequenceBuilder } from '../components/campaigns/ScriptSequenceBuilder';

import { DeviceStreamGrid } from '../components/common/DeviceStreamGrid';

import { CampaignConfig } from '../types/pages/Campaign_Types';
import { getScriptDisplayName, formatExecutionDuration, getLogsUrl, getStatusChip } from '../utils/executionUtils';

const RunCampaigns: React.FC = () => {
  // Hooks
  const {
    campaignConfig,
    updateCampaignConfig,
    resetCampaignConfig,
    availableScripts,
    aiTestCasesInfo,
    addScript,
    removeScript,

    updateScriptConfiguration,
    scriptAnalysisCache,
    loadScriptAnalysis,
    validateCampaignConfig,
    executeCampaign,
    isExecuting,
    currentExecution,
    campaignHistory,
    refreshCampaignHistory,
    isLoading,
    error,
  } = useCampaign();

  const { getAllHosts, getDevicesFromHost } = useHostManager();
  const { showInfo, showSuccess, showError } = useToast();

  // Local state
  const [activeStep, setActiveStep] = useState(0);
  const [showBuilder, setShowBuilder] = useState(false);

  // Get hosts for device selection
  const allHosts = getAllHosts();

  // Steps for campaign builder
  const steps = [
    'Campaign Configuration',
    'Script Sequence',
    'Review & Execute',
  ];

  // Load data on mount
  useEffect(() => {
    // Scripts are loaded automatically by useCampaign hook - no need to call again
    // Note: Campaign history is managed locally, no API call needed
  }, []);

  // AI test cases info is now loaded directly from useCampaign hook - no separate API call needed

  // Validation
  const validation = validateCampaignConfig();
  const canExecute = validation.valid && campaignConfig.script_configurations && campaignConfig.script_configurations.length > 0;

  // Handlers
  const handleStartBuilder = () => {
    setShowBuilder(true);
    setActiveStep(0);
    
    // Generate default campaign ID if not set
    if (!campaignConfig.campaign_id) {
      const timestamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
      updateCampaignConfig({
        campaign_id: `campaign-${timestamp}`,
        name: `Test Campaign ${timestamp}`,
      });
    }
  };

  const handleCancelBuilder = () => {
    setShowBuilder(false);
    setActiveStep(0);
    resetCampaignConfig();
  };

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleExecuteCampaign = async () => {
    if (!canExecute) {
      showError('Please complete campaign configuration');
      return;
    }

    try {
      showInfo(`Starting campaign: ${campaignConfig.name}`);
      
      const result = await executeCampaign(campaignConfig as CampaignConfig);
      
      if (result.success) {
        showSuccess(`Campaign started successfully: ${result.execution_id}`);
        setShowBuilder(false);
        setActiveStep(0);
      } else {
        showError(`Campaign failed to start: ${result.message}`);
      }
    } catch (error) {
      showError(`Campaign execution failed: ${error}`);
    }
  };

  // Get selected devices for stream display
  const getSelectedDevices = () => {
    if (campaignConfig.host && campaignConfig.device) {
      return [{ hostName: campaignConfig.host, deviceId: campaignConfig.device }];
    }
    return [];
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <CampaignConfigForm
            config={campaignConfig}
            hosts={allHosts}
            getDevicesFromHost={getDevicesFromHost}
            onConfigChange={updateCampaignConfig}
            errors={validation.errors}
          />
        );
      case 1:
        return (
          <ScriptSequenceBuilder
            scripts={campaignConfig.script_configurations || []}
            availableScripts={availableScripts}
            aiTestCasesInfo={aiTestCasesInfo}
            scriptAnalysisCache={scriptAnalysisCache}
            onAddScript={addScript}
            onRemoveScript={removeScript}

            onUpdateScript={updateScriptConfiguration}
            onLoadScriptAnalysis={loadScriptAnalysis}
          />
        );
      case 2:
        return (
          <Box>
            {/* Campaign Summary */}
            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Campaign Summary
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Campaign Name:</Typography>
                    <Typography variant="body1">{campaignConfig.name}</Typography>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Device:</Typography>
                    <Typography variant="body1">
                      {campaignConfig.host}:{campaignConfig.device}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Scripts:</Typography>
                    <Typography variant="body1">
                      {campaignConfig.script_configurations?.length || 0} scripts
                    </Typography>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Timeout:</Typography>
                    <Typography variant="body1">
                      {campaignConfig.execution_config?.timeout_minutes} minutes
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Device Stream Preview */}
            {getSelectedDevices().length > 0 && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Device Preview
                  </Typography>
                  <DeviceStreamGrid
                    devices={getSelectedDevices()}
                    allHosts={allHosts}
                    getDevicesFromHost={getDevicesFromHost}
                    maxColumns={1}
                  />
                </CardContent>
              </Card>
            )}

            {/* Validation Errors */}
            {!validation.valid && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Please fix the following issues:
                </Typography>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {validation.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </Alert>
            )}
          </Box>
        );
      default:
        return null;
    }
  };

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>
        Campaign Runner
      </Typography>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {/* Campaign Builder / Execution */}
        <Grid item xs={12}>
          <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Campaign Execution
              </Typography>

              {!showBuilder && !currentExecution ? (
                // Show launch button when builder is not active
                <Box display="flex" justifyContent="center" py={2}>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<LaunchIcon />}
                    onClick={handleStartBuilder}
                    disabled={isLoading}
                  >
                    {isLoading ? <CircularProgress size={20} /> : 'Build Campaign'}
                  </Button>
                </Box>
              ) : currentExecution ? (
                // Show simple execution progress (same as RunTests.tsx)
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Campaign Execution: {currentExecution.campaign_name}
                  </Typography>
                  
                  {/* Simple progress indicator (same as RunTests.tsx) */}
                  {isExecuting && (
                    <Box sx={{ mb: 2 }}>
                      <Card variant="outlined">
                        <CardContent sx={{ py: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Campaign Progress: {currentExecution.completed_scripts}/{currentExecution.total_scripts} scripts completed 
                            ({currentExecution.successful_scripts} successful)
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={`${currentExecution.hostName}:${currentExecution.deviceId}`}
                              color="warning"
                              size="small"
                              icon={<CircularProgress size={16} />}
                            />
                            {currentExecution.current_script && (
                              <Chip
                                label={`Running: ${getScriptDisplayName(currentExecution.current_script, aiTestCasesInfo)}`}
                                color="primary"
                                size="small"
                              />
                            )}
                          </Box>
                        </CardContent>
                      </Card>
                    </Box>
                  )}
                  
                  {/* Campaign completion status */}
                  {!isExecuting && currentExecution.status === 'completed' && (
                    <Alert severity={currentExecution.overall_success ? "success" : "error"} sx={{ mb: 2 }}>
                      Campaign {currentExecution.overall_success ? 'completed successfully' : 'failed'}! 
                      {currentExecution.successful_scripts}/{currentExecution.total_scripts} scripts successful.
                    </Alert>
                  )}
                </Box>
              ) : (
                // Show campaign builder
                <Box>
                  <Stepper activeStep={activeStep} orientation="vertical">
                    {steps.map((label, index) => (
                      <Step key={label}>
                        <StepLabel>{label}</StepLabel>
                        <StepContent>
                          <Box sx={{ mb: 2 }}>
                            {renderStepContent(index)}
                          </Box>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            {index === steps.length - 1 ? (
                              <Button
                                variant="contained"
                                onClick={handleExecuteCampaign}
                                disabled={!canExecute || isExecuting}
                                startIcon={isExecuting ? <CircularProgress size={16} /> : <LaunchIcon />}
                              >
                                {isExecuting ? 'Executing...' : 'Execute Campaign'}
                              </Button>
                            ) : (
                              <Button
                                variant="contained"
                                onClick={handleNext}
                              >
                                Next
                              </Button>
                            )}
                            
                            {index > 0 && (
                              <Button onClick={handleBack}>
                                Back
                              </Button>
                            )}
                            
                            <Button
                              onClick={handleCancelBuilder}
                              color="inherit"
                            >
                              Cancel
                            </Button>
                          </Box>
                        </StepContent>
                      </Step>
                    ))}
                  </Stepper>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Campaign History */}
        <Grid item xs={12}>
          <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6">
                  Campaign History
                </Typography>
                <Button
                  size="small"
                  onClick={refreshCampaignHistory}
                  disabled={isLoading}
                  startIcon={<HistoryIcon />}
                >
                  Refresh
                </Button>
              </Box>

              {campaignHistory.length === 0 ? (
                <Box
                  sx={{
                    p: 2,
                    textAlign: 'center',
                    borderRadius: 1,
                    backgroundColor: 'background.default',
                  }}
                >
                  <Typography variant="body2" color="textSecondary">
                    No campaign executions yet
                  </Typography>
                </Box>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small" sx={{ '& .MuiTableCell-root': { py: 0.5 } }}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Campaign</TableCell>
                        <TableCell>Device</TableCell>
                        <TableCell>Scripts</TableCell>
                        <TableCell>Start Time</TableCell>
                        <TableCell>Duration</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Success Rate</TableCell>
                        <TableCell>Report</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {campaignHistory.map((campaign) => (
                        <TableRow
                          key={campaign.id}
                          sx={{ '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04) !important' } }}
                        >
                          <TableCell>
                            <Typography variant="body2">
                              {campaign.campaign_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {campaign.campaign_id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {campaign.hostName}:{campaign.deviceId}
                            {campaign.deviceModel && (
                              <Typography variant="caption" display="block" color="text.secondary">
                                ({campaign.deviceModel})
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {campaign.successful_scripts}/{campaign.total_scripts}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ({campaign.failed_scripts} failed)
                            </Typography>
                          </TableCell>
                          <TableCell>{campaign.startTime}</TableCell>
                          <TableCell>
                            {campaign.duration || formatExecutionDuration(campaign.startTime, campaign.endTime)}
                          </TableCell>
                          <TableCell>
                            {getStatusChip(campaign.status)}
                          </TableCell>
                          <TableCell>
                            {campaign.total_scripts > 0 
                              ? `${((campaign.successful_scripts / campaign.total_scripts) * 100).toFixed(0)}%`
                              : 'N/A'
                            }
                          </TableCell>
                          <TableCell>
                            {campaign.reportUrl ? (
                              <Box sx={{ display: 'flex', gap: 1 }}>
                                <Chip
                                  label="Report"
                                  component="a"
                                  href={campaign.reportUrl}
                                  target="_blank"
                                  clickable
                                  size="small"
                                  sx={{ cursor: 'pointer' }}
                                  icon={<LinkIcon />}
                                  color="primary"
                                  variant="outlined"
                                />
                                {campaign.logsUrl && (
                                  <Chip
                                    label="Logs"
                                    size="small"
                                    clickable
                                    onClick={() => window.open(campaign.logsUrl || getLogsUrl(campaign.reportUrl!), '_blank')}
                                    color="secondary"
                                    variant="outlined"
                                  />
                                )}
                              </Box>
                            ) : (
                              <Chip label="No Report" size="small" variant="outlined" disabled />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RunCampaigns;
