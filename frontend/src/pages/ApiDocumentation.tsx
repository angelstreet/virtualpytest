import { Box, FormControl, IconButton, InputLabel, MenuItem, Select, SelectChangeEvent, Tooltip, Typography } from '@mui/material';
import { OpenInNew, Refresh } from '@mui/icons-material';
import React, { useState } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface ApiDoc {
  title: string;
  filename: string;
  category: 'SERVER' | 'HOST';
}

const ApiDocumentation: React.FC = () => {
  // Available API documentation
  const apiDocs: ApiDoc[] = [
    { title: 'All APIs', filename: 'index', category: 'SERVER' },
    { title: 'SERVER - Device Management', filename: 'server-device-management', category: 'SERVER' },
    { title: 'SERVER - Campaign Management', filename: 'server-campaign-management', category: 'SERVER' },
    { title: 'SERVER - Core System', filename: 'server-core-system', category: 'SERVER' },
    { title: 'SERVER - Navigation Management', filename: 'server-navigation-management', category: 'SERVER' },
    { title: 'SERVER - Testcase Management', filename: 'server-testcase-management', category: 'SERVER' },
    { title: 'SERVER - Script Management', filename: 'server-script-management', category: 'SERVER' },
    { title: 'SERVER - Requirements Management', filename: 'server-requirements-management', category: 'SERVER' },
    { title: 'SERVER - AI Analysis', filename: 'server-ai-analysis', category: 'SERVER' },
    { title: 'SERVER - Metrics & Analytics', filename: 'server-metrics-analytics', category: 'SERVER' },
    { title: 'SERVER - Deployment & Scheduling', filename: 'server-deployment-scheduling', category: 'SERVER' },
    { title: 'SERVER - User Interface Management', filename: 'server-user-interface-management', category: 'SERVER' },
    { title: 'HOST - Testcase Execution', filename: 'host-testcase-execution', category: 'HOST' },
    { title: 'HOST - AI Exploration', filename: 'host-ai-exploration', category: 'HOST' },
    { title: 'HOST - Verification Suite', filename: 'host-verification-suite', category: 'HOST' },
  ];

  // Default to index (all APIs)
  const [selectedDoc, setSelectedDoc] = useState<string>('index');

  const handleDocChange = (event: SelectChangeEvent<string>) => {
    setSelectedDoc(event.target.value);
  };

  const selectedDocData = apiDocs.find(d => d.filename === selectedDoc);

  // Get the documentation URL (served from backend)
  const getDocUrl = () => {
    // Docs are served by the backend server at /docs/openapi/docs/
    // Use buildServerUrl to respect selected server from ServerSelector
    return buildServerUrl(`/docs/openapi/docs/${selectedDoc}.html`);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Doc Selector */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl sx={{ minWidth: 350 }}>
          <InputLabel id="doc-select-label">Select API Documentation</InputLabel>
          <Select
            labelId="doc-select-label"
            id="doc-select"
            value={selectedDoc}
            label="Select API Documentation"
            onChange={handleDocChange}
          >
            {apiDocs.map((doc) => (
              <MenuItem key={doc.filename} value={doc.filename}>
                {doc.title}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="textSecondary">
            OpenAPI 3.0 Documentation
          </Typography>
          <Tooltip title="Refresh documentation">
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
              onClick={() => window.open(getDocUrl(), '_blank')}
              color="primary"
              size="medium"
            >
              <OpenInNew />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Documentation iframe */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        {selectedDocData && (
          <iframe
            key={selectedDoc} // Force reload on change
            src={getDocUrl()}
            width="100%"
            height="100%"
            frameBorder="0"
            title={selectedDocData.title}
            style={{
              border: 'none',
              display: 'block',
            }}
          />
        )}
      </Box>
    </Box>
  );
};

export default ApiDocumentation;

