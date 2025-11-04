import React from 'react';
import { Box, Grid, Stack } from '@mui/material';
import { MCPPlaygroundHeader } from '../components/mcp/MCPPlaygroundHeader';
import { MCPPromptInput } from '../components/mcp/MCPPromptInput';
import { MCPQuickActions } from '../components/mcp/MCPQuickActions';
import { MCPExecutionResult } from '../components/mcp/MCPExecutionResult';
import { MCPCommandHistory } from '../components/mcp/MCPCommandHistory';
import { PromptDisambiguation } from '../components/ai/PromptDisambiguation';
import { useMCPPlaygroundPage } from '../hooks/pages/useMCPPlaygroundPage';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { useTheme } from '../contexts/ThemeContext';
import { BuilderPageLayout, BuilderMainContainer } from '../components/common/builder';

const MCPPlaygroundContent: React.FC = () => {
  const { actualMode } = useTheme();
  const hookData = useMCPPlaygroundPage();
  
  // Wrapper for isDeviceLocked to match expected signature
  const isDeviceLocked = (deviceKey: string) => {
    const [hostName] = deviceKey.includes(':')
      ? deviceKey.split(':')
      : [deviceKey, 'device1'];
    const host = hookData.availableHosts.find((h: any) => h.host_name === hostName);
    return host ? hookData.availableHosts.some((h: any) => 
      h.host_name === hostName && h.isLocked
    ) : false;
  };
  
  return (
    <BuilderPageLayout>
      {/* MCP Playground Header - COPIED from TestCaseBuilderHeader, STRIPPED unused parts */}
      <MCPPlaygroundHeader
        actualMode={actualMode}
        selectedHost={hookData.selectedHost}
        selectedDeviceId={hookData.selectedDeviceId}
        isControlActive={hookData.isControlActive}
        isControlLoading={hookData.isControlLoading}
        availableHosts={hookData.availableHosts}
        isDeviceLocked={isDeviceLocked}
        handleDeviceSelect={hookData.handleDeviceSelect}
        handleDeviceControl={hookData.handleDeviceControl as any}
        compatibleInterfaceNames={hookData.compatibleInterfaceNames}
        userinterfaceName={hookData.userinterfaceName}
        setUserinterfaceName={hookData.setUserinterfaceName}
        isLoadingTree={hookData.isLoadingTree}
        currentTreeId={hookData.currentTreeId}
      />

      {/* REUSE BuilderMainContainer - Same as TestCaseBuilder */}
      <BuilderMainContainer>
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 3,
          }}
        >
          <Box sx={{ maxWidth: '1600px', mx: 'auto' }}>
            <Stack spacing={3}>
              {/* ROW 1: Prompt (2/3) + Quick Actions (1/3) */}
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <MCPPromptInput
                    prompt={hookData.prompt}
                    setPrompt={hookData.setPrompt}
                    isGenerating={hookData.isGenerating}
                    handleGenerate={hookData.handleGenerate}
                    isControlActive={hookData.isControlActive}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <MCPQuickActions
                    navNodes={hookData.navNodes}
                    availableActions={hookData.availableActions}
                    availableVerifications={hookData.availableVerifications}
                    setPrompt={hookData.setPrompt}
                    isControlActive={hookData.isControlActive}
                  />
                </Grid>
              </Grid>
              
              {/* ROW 2: Execution Result (full width) */}
              <Grid container>
                <Grid item xs={12}>
                  <MCPExecutionResult
                    unifiedExecution={hookData.unifiedExecution}
                    executionResult={hookData.executionResult}
                  />
                </Grid>
              </Grid>
              
              {/* ROW 3: Command History (full width) */}
              <Grid container>
                <Grid item xs={12}>
                  <MCPCommandHistory
                    commandHistory={hookData.commandHistory}
                    setPrompt={hookData.setPrompt}
                    clearHistory={hookData.clearHistory}
                  />
                </Grid>
              </Grid>
            </Stack>
          </Box>
        </Box>
      </BuilderMainContainer>
      
      {/* AI Disambiguation Modal */}
      {hookData.disambiguationData && (
        <PromptDisambiguation
          ambiguities={hookData.disambiguationData.ambiguities}
          autoCorrections={hookData.disambiguationData.auto_corrections}
          availableNodes={hookData.disambiguationData.available_nodes}
          onResolve={hookData.handleDisambiguationResolve}
          onCancel={hookData.handleDisambiguationCancel}
          onEditPrompt={() => {
            hookData.handleDisambiguationCancel();
          }}
        />
      )}
    </BuilderPageLayout>
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
