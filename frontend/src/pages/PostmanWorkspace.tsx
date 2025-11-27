import { Box, FormControl, IconButton, InputLabel, MenuItem, Select, SelectChangeEvent, Tooltip, Typography } from '@mui/material';
import { OpenInNew } from '@mui/icons-material';
import React, { useState } from 'react';

interface Collection {
  title: string;
  uid: string;
  name: string;
}

const PostmanWorkspace: React.FC = () => {
  // Postman workspace ID
  const workspaceId = '91dbec69-5756-413d-a530-a97b9cadf615';
  const postmanUrl = 'https://www.postman.com';

  // Available collections
  const collections: Collection[] = [
    {
      title: 'All Collections',
      uid: 'workspace',
      name: 'VirtualPyTest API Testing'
    },
    {
      title: 'SERVER - Device Management',
      uid: '91fc31ac-0a25-4e01-8e9f-5123477a891d',
      name: 'server-device-management'
    },
    {
      title: 'SERVER - Campaign Management',
      uid: '386ce4b3-afb5-4f4c-b831-7feaab51f39c',
      name: 'server-campaign-management'
    },
    {
      title: 'SERVER - Core System & Health',
      uid: '0d39c723-518d-4ec6-8085-d28722af2e79',
      name: 'server-core-system'
    },
    {
      title: 'SERVER - Navigation Management',
      uid: '02dad45d-3c67-446a-918b-df5edbdd07ac',
      name: 'server-navigation-management'
    },
    {
      title: 'SERVER - Testcase Management',
      uid: 'dd6df8c6-3014-4923-8ec3-f888eb0e4184',
      name: 'server-testcase-management'
    },
    {
      title: 'SERVER - Script Management',
      uid: 'c5d1e382-a2f6-4beb-8774-c8bcca03ab26',
      name: 'server-script-management'
    },
    {
      title: 'SERVER - Requirements Management',
      uid: '19399375-c6db-463c-a77e-3844c45076dd',
      name: 'server-requirements-management'
    },
    {
      title: 'SERVER - AI & Analysis',
      uid: 'ef97e08d-6cdc-432e-a27b-f52e9d52a3c2',
      name: 'server-ai-analysis'
    },
    {
      title: 'HOST - System & Health',
      uid: '8a68d2fc-438f-4ed1-9c4b-81e693cf5395',
      name: 'host-system-health'
    },
    {
      title: 'HOST - Device Control',
      uid: 'cd0b4889-e3df-4e31-bd12-7357c79ce6d2',
      name: 'host-device-control'
    },
    {
      title: 'HOST - Testcase Execution',
      uid: 'd600c890-8b11-42a4-9022-c0af48f7d157',
      name: 'host-testcase-execution'
    },
    {
      title: 'HOST - AI Exploration',
      uid: 'f5f598fc-15e1-4822-a1fa-e84b8fda5079',
      name: 'host-ai-exploration'
    },
    {
      title: 'HOST - Verification Suite',
      uid: 'd434ffc4-f59e-4b70-b899-a2cbdf39e542',
      name: 'host-verification-suite'
    }
  ];

  // Default to workspace view
  const [selectedCollection, setSelectedCollection] = useState<string>('workspace');

  const handleCollectionChange = (event: SelectChangeEvent<string>) => {
    setSelectedCollection(event.target.value);
  };

  const selectedCollectionData = collections.find(c => c.uid === selectedCollection);

  // Build the iframe URL
  const getIframeUrl = () => {
    if (selectedCollection === 'workspace') {
      // Show entire workspace
      return `${postmanUrl}/workspace/${workspaceId}`;
    } else {
      // Show specific collection in workspace context
      return `${postmanUrl}/workspace/${workspaceId}/collection/${selectedCollection}`;
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Collection Selector */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl sx={{ minWidth: 300 }}>
          <InputLabel id="collection-select-label">Select Collection</InputLabel>
          <Select
            labelId="collection-select-label"
            id="collection-select"
            value={selectedCollection}
            label="Select Collection"
            onChange={handleCollectionChange}
          >
            {collections.map((collection) => (
              <MenuItem key={collection.uid} value={collection.uid}>
                {collection.title}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="textSecondary">
            Postman Workspace (Read-Only View)
          </Typography>
          <Tooltip title="Open Postman Workspace in new tab">
            <IconButton
              onClick={() => window.open(`${postmanUrl}/workspace/${workspaceId}`, '_blank')}
              color="primary"
              size="medium"
            >
              <OpenInNew />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Postman iframe */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        {selectedCollectionData && (
          <iframe
            src={getIframeUrl()}
            width="100%"
            height="100%"
            frameBorder="0"
            title={selectedCollectionData.title}
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

export default PostmanWorkspace;

