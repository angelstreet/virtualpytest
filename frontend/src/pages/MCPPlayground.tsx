import React from 'react';
import { Box, Grid, Stack, Container } from '@mui/material';
import { MCPDeviceSelector } from '../components/mcp/MCPDeviceSelector';
import { MCPPromptInput } from '../components/mcp/MCPPromptInput';
import { MCPQuickActions } from '../components/mcp/MCPQuickActions';
import { MCPExecutionResult } from '../components/mcp/MCPExecutionResult';
import { MCPCommandHistory } from '../components/mcp/MCPCommandHistory';
import { PromptDisambiguation } from '../components/ai/PromptDisambiguation';
import { useTheme } from '../contexts/ThemeContext';
import { useMCPPlaygroundPage } from '../hooks/pages/useMCPPlaygroundPage';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';

const MCPPlaygroundContent: React.FC = () => {
  const { actualMode } = useTheme();
  const hookData = useMCPPlaygroundPage();
  
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        bgcolor: 'background.default',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          height: 42,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          px: { xs: 2, md: 3 },
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
         
          <Box>
            <Box sx={{ fontSize: '1rem', fontWeight: 600 }}>
              MCP - Model Context Protocol
            </Box>
            
          </Box>
        </Box>
      </Box>
      
      {/* Main Content */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: { xs: 2, md: 3 },
        }}
      >
        <Container maxWidth="xl" disableGutters>
          <Grid container spacing={{ xs: 2, md: 3 }}>
            {/* LEFT PANEL: Device Selection + History (Desktop) */}
            <Grid item xs={12} md={4} lg={3}>
              <Stack spacing={{ xs: 2, md: 3 }}>
                <MCPDeviceSelector
                  selectedHost={hookData.selectedHost}
                  selectedDeviceId={hookData.selectedDeviceId}
                  userinterfaceName={hookData.userinterfaceName}
                  setUserinterfaceName={hookData.setUserinterfaceName}
                  availableHosts={hookData.availableHosts}
                  compatibleInterfaceNames={hookData.compatibleInterfaceNames}
                  isControlActive={hookData.isControlActive}
                  isControlLoading={hookData.isControlLoading}
                  handleDeviceSelect={hookData.handleDeviceSelect}
                  handleDeviceControl={hookData.handleDeviceControl}
                  defaultCollapsed={false}
                />
                <Box sx={{ display: { xs: 'none', lg: 'block' } }}>
                  <MCPCommandHistory
                    commandHistory={hookData.commandHistory}
                    setPrompt={hookData.setPrompt}
                    clearHistory={hookData.clearHistory}
                  />
                </Box>
              </Stack>
            </Grid>
            
            {/* CENTER PANEL: Prompt + Execution */}
            <Grid item xs={12} md={8} lg={6}>
              <Stack spacing={{ xs: 2, md: 3 }}>
                <MCPPromptInput
                  prompt={hookData.prompt}
                  setPrompt={hookData.setPrompt}
                  isGenerating={hookData.isGenerating}
                  handleGenerate={hookData.handleGenerate}
                  isControlActive={hookData.isControlActive}
                />
                <MCPExecutionResult
                  unifiedExecution={hookData.unifiedExecution}
                  executionResult={hookData.executionResult}
                />
              </Stack>
            </Grid>
            
            {/* RIGHT PANEL: Quick Actions (Desktop) */}
            <Grid item xs={12} lg={3} sx={{ display: { xs: 'none', lg: 'block' } }}>
              <MCPQuickActions
                navNodes={hookData.navNodes}
                availableActions={hookData.availableActions}
                availableVerifications={hookData.availableVerifications}
                setPrompt={hookData.setPrompt}
              />
            </Grid>
            
            {/* MOBILE/TABLET: Quick Actions (full-width) */}
            <Grid item xs={12} sx={{ display: { xs: 'block', lg: 'none' } }}>
              <MCPQuickActions
                navNodes={hookData.navNodes}
                availableActions={hookData.availableActions}
                availableVerifications={hookData.availableVerifications}
                setPrompt={hookData.setPrompt}
              />
            </Grid>
            
            {/* MOBILE/TABLET: History (full-width) */}
            <Grid item xs={12} sx={{ display: { xs: 'block', lg: 'none' } }}>
              <MCPCommandHistory
                commandHistory={hookData.commandHistory}
                setPrompt={hookData.setPrompt}
                clearHistory={hookData.clearHistory}
              />
            </Grid>
          </Grid>
        </Container>
      </Box>
      
      {/* AI Disambiguation Modal */}
      {hookData.disambiguationData && (
        <PromptDisambiguation
          ambiguities={hookData.disambiguationData.ambiguities}
          autoCorrections={hookData.disambiguationData.auto_corrections}
          availableNodes={hookData.disambiguationData.available_nodes}
          onResolve={hookData.handleDisambiguationResolve}
          onCancel={hookData.handleDisambiguationCancel}
          onEditPrompt={(newPrompt) => {
            hookData.setPrompt(newPrompt);
            hookData.handleDisambiguationCancel();
          }}
        />
      )}
    </Box>
  );
};

const MCPPlayground: React.FC = () => {
  return (
    <NavigationConfigProvider>
      <NavigationEditorProvider>
        <MCPPlaygroundContent />
      </NavigationEditorProvider>
    </NavigationConfigProvider>
  );
};

export default MCPPlayground;

