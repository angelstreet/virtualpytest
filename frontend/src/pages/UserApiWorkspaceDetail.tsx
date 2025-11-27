import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Checkbox,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  ArrowBack,
  ExpandMore,
  PlayArrow,
} from '@mui/icons-material';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface Request {
  id: string;
  name: string;
  fullName: string;
  method: string;
  path: string;
  description: string;
}

interface Collection {
  id: string;
  name: string;
  description: string;
  requestCount: number;
  requests?: Request[];
}

interface Workspace {
  id: string;
  name: string;
  description: string;
}

const UserApiWorkspaceDetail: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedRequests, setSelectedRequests] = useState<Set<string>>(new Set());
  const [expandedCollections, setExpandedCollections] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadingRequests, setLoadingRequests] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  useEffect(() => {
    loadWorkspaceAndCollections();
  }, [workspaceId]);

  const loadWorkspaceAndCollections = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load workspaces to get workspace details
      const wsResponse = await fetch(buildServerUrl('/server/postman/workspaces'));
      const wsData = await wsResponse.json();
      
      if (wsData.success) {
        const ws = wsData.workspaces.find((w: Workspace) => w.id === workspaceId);
        if (ws) {
          setWorkspace(ws);
        } else {
          setError('Workspace not found');
          return;
        }
      }

      // Load collections
      const collResponse = await fetch(buildServerUrl(`/server/postman/workspaces/${workspaceId}/collections`));
      const collData = await collResponse.json();
      
      if (collData.success) {
        setCollections(collData.collections);
      } else {
        setError(collData.error || 'Failed to load collections');
      }
    } catch (err) {
      setError('Error connecting to server');
      console.error('Error loading workspace:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadCollectionRequests = async (collectionId: string) => {
    setLoadingRequests(prev => new Set(prev).add(collectionId));
    
    try {
      const response = await fetch(buildServerUrl(`/server/postman/collections/${collectionId}/requests?workspace_id=${workspaceId}`));
      const data = await response.json();
      
      if (data.success) {
        // Update collection with requests
        setCollections(prev =>
          prev.map(coll =>
            coll.id === collectionId
              ? { ...coll, requests: data.requests }
              : coll
          )
        );
        
        // Expand the collection
        setExpandedCollections(prev => new Set(prev).add(collectionId));
      }
    } catch (err) {
      console.error('Error loading requests:', err);
    } finally {
      setLoadingRequests(prev => {
        const newSet = new Set(prev);
        newSet.delete(collectionId);
        return newSet;
      });
    }
  };

  const handleCollectionToggle = (collectionId: string) => {
    const collection = collections.find(c => c.id === collectionId);
    
    if (!collection) return;
    
    // If not yet loaded, load requests first
    if (!collection.requests) {
      loadCollectionRequests(collectionId);
    } else {
      // Toggle expansion
      setExpandedCollections(prev => {
        const newSet = new Set(prev);
        if (newSet.has(collectionId)) {
          newSet.delete(collectionId);
        } else {
          newSet.add(collectionId);
        }
        return newSet;
      });
    }
  };

  const handleRequestToggle = (requestId: string) => {
    setSelectedRequests(prev => {
      const newSet = new Set(prev);
      if (newSet.has(requestId)) {
        newSet.delete(requestId);
      } else {
        newSet.add(requestId);
      }
      return newSet;
    });
  };

  const handleCollectionSelectAll = (collectionId: string) => {
    const collection = collections.find(c => c.id === collectionId);
    if (!collection || !collection.requests) return;
    
    const collectionRequestIds = collection.requests.map(r => r.id);
    const allSelected = collectionRequestIds.every(id => selectedRequests.has(id));
    
    setSelectedRequests(prev => {
      const newSet = new Set(prev);
      if (allSelected) {
        // Deselect all
        collectionRequestIds.forEach(id => newSet.delete(id));
      } else {
        // Select all
        collectionRequestIds.forEach(id => newSet.add(id));
      }
      return newSet;
    });
  };

  const handleRunTests = async () => {
    if (selectedRequests.size === 0) {
      alert('Please select at least one endpoint to test');
      return;
    }

    setRunning(true);
    setTestResult(null);

    try {
      // Gather selected endpoints
      const endpoints: any[] = [];
      
      collections.forEach(collection => {
        if (collection.requests) {
          collection.requests.forEach(request => {
            if (selectedRequests.has(request.id)) {
              endpoints.push({
                method: request.method,
                path: request.path,
                name: request.name,
              });
            }
          });
        }
      });

      const response = await fetch(buildServerUrl('/server/postman/test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspaceId,
          workspaceName: workspace?.name,
          endpoints,
        }),
      });

      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      console.error('Error running tests:', err);
      setTestResult({ success: false, error: 'Failed to run tests' });
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!workspace) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Workspace not found</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/api/workspaces')} sx={{ mt: 2 }}>
          Back to Workspaces
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>
      {/* Compact Header */}
      <Box sx={{ px: 3, pt: 2, pb: 1 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/api/workspaces')}
          size="small"
          sx={{ mb: 0.5 }}
        >
          Back to Workspaces
        </Button>
        
        <Typography variant="h5">
          {workspace.name}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mt: 1 }}>
            {error}
          </Alert>
        )}

        {testResult && (
          <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mt: 1 }} onClose={() => setTestResult(null)}>
            {testResult.success ? testResult.message : testResult.error}
            {testResult.note && (
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                {testResult.note}
              </Typography>
            )}
          </Alert>
        )}
      </Box>

      {/* Sticky Action Bar */}
      <Box 
        sx={{ 
          position: 'sticky',
          top: 0,
          zIndex: 10,
          bgcolor: 'background.default',
          borderBottom: 1,
          borderColor: 'divider',
          px: 3,
          py: 1.5,
          boxShadow: 1
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            variant="contained"
            size="large"
            fullWidth
            startIcon={running ? <CircularProgress size={20} /> : <PlayArrow />}
            onClick={handleRunTests}
            disabled={selectedRequests.size === 0 || running}
          >
            Run Now ({selectedRequests.size})
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ ml: 2, minWidth: 100, textAlign: 'right' }}>
            {collections.length} collections
          </Typography>
        </Box>
      </Box>

      {/* Scrollable Collections Area */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 3, py: 2 }}>
        {collections.length === 0 && (
          <Card>
            <CardContent>
              <Typography variant="body1" color="text.secondary" align="center">
                No collections found in this workspace.
              </Typography>
            </CardContent>
          </Card>
        )}

        {collections.map((collection) => {
        const isExpanded = expandedCollections.has(collection.id);
        const isLoadingRequests = loadingRequests.has(collection.id);
        const allSelected = collection.requests?.every(r => selectedRequests.has(r.id)) || false;
        const someSelected = collection.requests?.some(r => selectedRequests.has(r.id)) || false;

        return (
          <Accordion
            key={collection.id}
            expanded={isExpanded}
            onChange={() => handleCollectionToggle(collection.id)}
            sx={{ mb: 1 }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                {collection.requests && (
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected && !allSelected}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCollectionSelectAll(collection.id);
                    }}
                  />
                )}
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1">{collection.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {collection.description || 'No description'}
                  </Typography>
                </Box>
                <Chip
                  label={`${collection.requestCount} endpoints`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {isLoadingRequests && (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              )}
              
              {collection.requests && (
                <List dense>
                  {collection.requests.map((request) => (
                    <ListItem key={request.id} disablePadding>
                      <ListItemButton onClick={() => handleRequestToggle(request.id)}>
                        <ListItemIcon>
                          <Checkbox
                            checked={selectedRequests.has(request.id)}
                            edge="start"
                            tabIndex={-1}
                            disableRipple
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Chip
                                label={request.method}
                                size="small"
                                color={
                                  request.method === 'GET' ? 'success' :
                                  request.method === 'POST' ? 'primary' :
                                  request.method === 'PUT' ? 'warning' :
                                  request.method === 'DELETE' ? 'error' :
                                  'default'
                                }
                                sx={{ minWidth: 60, fontFamily: 'monospace', fontSize: '0.7rem' }}
                              />
                              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                {request.path}
                              </Typography>
                            </Box>
                          }
                          secondary={request.name}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              )}
            </AccordionDetails>
          </Accordion>
        );
      })}
      </Box>
    </Box>
  );
};

export default UserApiWorkspaceDetail;

