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
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  ArrowBack,
  ExpandMore,
  PlayArrow,
  CheckCircle,
  Schedule,
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

interface Environment {
  id: string;
  name: string;
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
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>('');
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

  // Auto-select first environment
  useEffect(() => {
    if (environments.length > 0 && !selectedEnvironment) {
      setSelectedEnvironment(environments[0].id);
    }
  }, [environments]);

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

      // Load environments
      const envResponse = await fetch(buildServerUrl(`/server/postman/workspaces/${workspaceId}/environments`));
      const envData = await envResponse.json();
      
      if (envData.success) {
        setEnvironments(envData.environments);
      } else {
        console.warn('Failed to load environments:', envData.error);
        // Don't set error - environments are optional
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

    if (!selectedEnvironment) {
      alert('Please select an environment (provides server URL)');
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
          environmentId: selectedEnvironment || undefined,
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
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/api/workspaces')}
          sx={{ mb: 2 }}
        >
          Back to Workspaces
        </Button>
        
        <Typography variant="h4" sx={{ mb: 1 }}>
          {workspace.name}
        </Typography>
        {workspace.description && (
          <Typography variant="body2" color="text.secondary">
            {workspace.description}
          </Typography>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {testResult && (
        <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mb: 2 }} onClose={() => setTestResult(null)}>
          {testResult.success ? testResult.message : testResult.error}
          {testResult.note && (
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              {testResult.note}
            </Typography>
          )}
        </Alert>
      )}

      {/* Environment Selector */}
      {environments.length > 0 && (
        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
          <InputLabel id="environment-select-label">Environment</InputLabel>
          <Select
            labelId="environment-select-label"
            id="environment-select"
            value={selectedEnvironment}
            label="Environment"
            onChange={(e) => setSelectedEnvironment(e.target.value)}
            MenuProps={{
              PaperProps: {
                style: {
                  maxHeight: 200,
                },
              },
            }}
          >
            {environments.map((env) => (
              <MenuItem key={env.id} value={env.id}>
                {env.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {/* Actions */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
        <Button
          variant="contained"
          startIcon={running ? <CircularProgress size={16} /> : <PlayArrow />}
          onClick={handleRunTests}
          disabled={selectedRequests.size === 0 || running || !selectedEnvironment}
        >
          Run Selected Tests ({selectedRequests.size})
        </Button>
        <Button
          variant="outlined"
          startIcon={<Schedule />}
          onClick={() => navigate('/deployments')}
          disabled={selectedRequests.size === 0}
        >
          Deploy to Schedule
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
          {collections.length} collections
        </Typography>
      </Box>

      {/* Collections */}
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

      {selectedRequests.size > 0 && (
        <Box sx={{ mt: 3 }}>
          <Alert severity="info">
            <Typography variant="body2">
              Results are stored in the database. To schedule recurring tests, go to Deployments.
            </Typography>
          </Alert>
        </Box>
      )}
    </Box>
  );
};

export default UserApiWorkspaceDetail;

