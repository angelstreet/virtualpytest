import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import { OpenInNew, Refresh, Security } from '@mui/icons-material';
import React from 'react';

const SecurityReports: React.FC = () => {
  // Get the security report URL (served as static files from frontend)
  const getReportUrl = () => {
    const url = '/docs/security/index.html';
    console.log('[SecurityReports] Loading iframe URL:', url);
    return url;
  };

  return (
    <Box sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header with actions */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2 }}>
        <Security color="primary" sx={{ fontSize: 28 }} />
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Security Reports
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="textSecondary">
            Bandit + Safety + npm audit
          </Typography>
          <Tooltip title="Refresh report">
            <IconButton
              onClick={() => window.location.reload()}
              color="primary"
              size="medium"
            >
              <Refresh />
            </IconButton>
          </Tooltip>
          <Tooltip title="Open in new tab">
            <IconButton
              onClick={() => window.open(getReportUrl(), '_blank')}
              color="primary"
              size="medium"
            >
              <OpenInNew />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Security Report iframe */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <iframe
          src={getReportUrl()}
          width="100%"
          height="100%"
          frameBorder="0"
          title="Security Reports"
          style={{
            border: 'none',
            display: 'block',
          }}
        />
      </Box>
    </Box>
  );
};

export default SecurityReports;


