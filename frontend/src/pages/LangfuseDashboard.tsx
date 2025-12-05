import { Box, IconButton, Tooltip, Typography, Alert, Button } from '@mui/material';
import { OpenInNew, Insights as LangfuseIcon } from '@mui/icons-material';
import React from 'react';

const LangfuseDashboard: React.FC = () => {
  // Get Langfuse URL from environment variable
  const langfuseUrl = (import.meta as any).env?.VITE_LANGFUSE_URL || 'http://localhost:3001';
  const langfuseEnabled = (import.meta as any).env?.VITE_LANGFUSE_ENABLED === 'true';

  if (!langfuseEnabled) {
    return (
      <Box sx={{ 
        height: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 3,
        p: 4,
      }}>
        <LangfuseIcon sx={{ fontSize: 80, color: 'text.secondary' }} />
        <Typography variant="h4" gutterBottom>
          Langfuse LLM Observability
        </Typography>
        <Alert severity="info" sx={{ maxWidth: 600 }}>
          <Typography variant="body1" gutterBottom>
            Langfuse is not enabled. To enable LLM observability:
          </Typography>
          <ol style={{ margin: '8px 0', paddingLeft: 20 }}>
            <li>Run the install script: <code>./scripts/langfuse_install.sh</code></li>
            <li>Add to <code>backend_server/.env</code>:
              <pre style={{ 
                background: '#f5f5f5', 
                padding: 8, 
                borderRadius: 4,
                marginTop: 4,
                fontSize: 12,
              }}>
{`LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...`}
              </pre>
            </li>
            <li>Add to <code>frontend/.env</code>:
              <pre style={{ 
                background: '#f5f5f5', 
                padding: 8, 
                borderRadius: 4,
                marginTop: 4,
                fontSize: 12,
              }}>
{`VITE_LANGFUSE_ENABLED=true
VITE_LANGFUSE_URL=http://localhost:3001`}
              </pre>
            </li>
            <li>Restart services</li>
          </ol>
        </Alert>
        <Button 
          variant="outlined" 
          href="/docs/ai agent/langfuse_integration"
          sx={{ mt: 2 }}
        >
          View Documentation
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ 
        p: 2, 
        borderBottom: '1px solid #e0e0e0', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <LangfuseIcon color="primary" />
          <Typography variant="h6">
            Langfuse - LLM Observability
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="textSecondary">
            Token Usage • Cost Tracking • Traces
          </Typography>
          <Tooltip title="Open Langfuse in new tab">
            <IconButton
              onClick={() => window.open(langfuseUrl, '_blank')}
              color="primary"
              size="medium"
            >
              <OpenInNew />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Dashboard iframe */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <iframe
          src={langfuseUrl}
          width="100%"
          height="100%"
          frameBorder="0"
          title="Langfuse Dashboard"
          style={{
            border: 'none',
            display: 'block',
          }}
        />
      </Box>
    </Box>
  );
};

export default LangfuseDashboard;

