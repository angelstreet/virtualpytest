import { Box, FormControl, IconButton, InputLabel, MenuItem, Select, SelectChangeEvent, Tooltip } from '@mui/material';
import { OpenInNew } from '@mui/icons-material';
import ApiIcon from '@mui/icons-material/Api';
import React, { useState } from 'react';

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

  // Get the documentation URL (served as static files from frontend)
  const getDocUrl = () => {
    // Docs are copied to public/docs/api/openapi/ during build
    const url = `/docs/api/openapi/${selectedDoc}.html`;
    console.log('[ApiDocumentation] Loading iframe URL:', url);
    console.log('[ApiDocumentation] Selected doc:', selectedDoc);
    return url;
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
          <Tooltip title="Open in new tab">
            <IconButton
              onClick={() => window.open(getDocUrl(), '_blank')}
              color="primary"
              size="medium"
            >
              <OpenInNew />
            </IconButton>
          </Tooltip>
          <Tooltip title="Open Postman Workspace">
            <IconButton
              onClick={() => window.open('https://www.postman.com/angelstreet-6173fb0b-1548216/virtualpytest-api-testing/overview', '_blank')}
              color="secondary"
              size="medium"
            >
              <ApiIcon />
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

