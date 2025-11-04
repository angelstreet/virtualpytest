import React from 'react';
import { Box, Grid, Stack, Container } from '@mui/material';
import { MCPPlaygroundProvider } from '../contexts/mcp/MCPPlaygroundContext';
import { MCPDeviceSelector } from '../components/mcp/MCPDeviceSelector';
import { MCPPromptInput } from '../components/mcp/MCPPromptInput';
import { MCPQuickActions } from '../components/mcp/MCPQuickActions';
import { MCPExecutionResult } from '../components/mcp/MCPExecutionResult';
import { MCPCommandHistory } from '../components/mcp/MCPCommandHistory';
import { PromptDisambiguation } from '../components/ai/PromptDisambiguation';
import { useMCPPlayground } from '../contexts/mcp/MCPPlaygroundContext';
import { useTheme } from '../contexts/ThemeContext';

const MCPPlaygroundContent: React.FC = () => {
  const { actualMode } = useTheme();
  const {
    disambiguationData,
    handleDisambiguationResolve,
    handleDisambiguationCancel,
  } = useMCPPlayground();
  
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
          height: 64,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          px: { xs: 2, md: 3 },
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 1,
              bgcolor: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '1.5rem',
            }}
          >
            🎤
          </Box>
          <Box>
            <Box sx={{ fontSize: '1.25rem', fontWeight: 600 }}>
              MCP Playground
            </Box>
            <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
              Voice-first device automation
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
                <MCPDeviceSelector defaultCollapsed={false} />
                <Box sx={{ display: { xs: 'none', lg: 'block' } }}>
                  <MCPCommandHistory />
                </Box>
              </Stack>
            </Grid>
            
            {/* CENTER PANEL: Prompt + Execution */}
            <Grid item xs={12} md={8} lg={6}>
              <Stack spacing={{ xs: 2, md: 3 }}>
                <MCPPromptInput />
                <MCPExecutionResult />
              </Stack>
            </Grid>
            
            {/* RIGHT PANEL: Quick Actions (Desktop) */}
            <Grid item xs={12} lg={3} sx={{ display: { xs: 'none', lg: 'block' } }}>
              <MCPQuickActions />
            </Grid>
            
            {/* MOBILE/TABLET: Quick Actions (full-width) */}
            <Grid item xs={12} sx={{ display: { xs: 'block', lg: 'none' } }}>
              <MCPQuickActions />
            </Grid>
            
            {/* MOBILE/TABLET: History (full-width) */}
            <Grid item xs={12} sx={{ display: { xs: 'block', lg: 'none' } }}>
              <MCPCommandHistory />
            </Grid>
          </Grid>
        </Container>
      </Box>
      
      {/* AI Disambiguation Modal */}
      {disambiguationData && (
        <PromptDisambiguation
          ambiguities={disambiguationData.ambiguities}
          autoCorrections={disambiguationData.auto_corrections}
          availableNodes={disambiguationData.available_nodes}
          onResolve={handleDisambiguationResolve}
          onCancel={handleDisambiguationCancel}
          onEditPrompt={(newPrompt) => {
            // TODO: Implement edit prompt handler
            console.log('Edit prompt:', newPrompt);
            handleDisambiguationCancel();
          }}
        />
      )}
    </Box>
  );
};

const MCPPlayground: React.FC = () => {
  return (
    <MCPPlaygroundProvider>
      <MCPPlaygroundContent />
    </MCPPlaygroundProvider>
  );
};

export default MCPPlayground;

