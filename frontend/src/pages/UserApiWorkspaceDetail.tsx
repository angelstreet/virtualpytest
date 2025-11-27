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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
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
  const [showResultsDialog, setShowResultsDialog] = useState(false);

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

  const loadCollectionRequests = async (collectionId: string, expand = true) => {
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
        if (expand) {
          setExpandedCollections(prev => new Set(prev).add(collectionId));
        }
        
        return data.requests;
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
    return null;
  };

  const handleCollectionToggle = (collectionId: string) => {
    const collection = collections.find(c => c.id === collectionId);
    
    if (!collection) return;
    
    // If not yet loaded, load requests first
    if (!collection.requests) {
      loadCollectionRequests(collectionId, true);
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

  const handleCollectionSelectAll = async (collectionId: string) => {
    const collection = collections.find(c => c.id === collectionId);
    if (!collection) return;
    
    let requests = collection.requests;
    
    // Load requests if not already loaded
    if (!requests) {
      requests = await loadCollectionRequests(collectionId, false);
    }
    
    if (!requests) return;
    
    const collectionRequestIds = requests.map((r: Request) => r.id);
    
    setSelectedRequests(prev => {
      const newSet = new Set(prev);
      // Check if all are currently selected
      const allSelected = collectionRequestIds.every((id: string) => prev.has(id));
      
      if (allSelected) {
        // Deselect all
        collectionRequestIds.forEach((id: string) => newSet.delete(id));
      } else {
        // Select all
        collectionRequestIds.forEach((id: string) => newSet.add(id));
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
      if (data.success && data.results) {
        setShowResultsDialog(true);
      }
    } catch (err) {
      console.error('Error running tests:', err);
      setTestResult({ success: false, error: 'Failed to run tests' });
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        position: 'fixed',
        top: 64,
        left: 38,
        right: 38,
        bottom: 35,
        overflow: 'hidden'
      }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!workspace) {
    return (
      <Box sx={{ 
        p: 2,
        position: 'fixed',
        top: 64,
        left: 38,
        right: 38,
        bottom: 35,
        overflow: 'hidden'
      }}>
        <Alert severity="error">Workspace not found</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/api/workspaces')} sx={{ mt: 1 }}>
          Back to Workspaces
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      position: 'fixed',
      top: 64,
      left: 38,
      right: 38,
      bottom: 35,
      overflow: 'hidden'
    }}>
      {/* Ultra-Compact Header with All Controls */}
      <Box 
        sx={{ 
          px: 3, 
          py: 0.5, 
          flexShrink: 0,
          bgcolor: 'background.default',
          borderBottom: 1,
          borderColor: 'divider',
          boxShadow: 1
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/api/workspaces')}
            size="small"
          >
            Back to Workspaces
          </Button>
          
          <Typography variant="h6">
            {workspace.name}
          </Typography>

          <Box sx={{ flex: 1 }} />
          
          <Typography variant="caption" color="text.secondary" sx={{ mr: 2 }}>
            {collections.length} collections
          </Typography>

          <Button
            variant="contained"
            startIcon={running ? <CircularProgress size={16} /> : <PlayArrow />}
            onClick={handleRunTests}
            disabled={selectedRequests.size === 0 || running}
          >
            Run Now ({selectedRequests.size})
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mt: 1 }}>
            {error}
          </Alert>
        )}

        {testResult && (
          <Alert 
            severity={testResult.success ? 'success' : 'error'} 
            sx={{ mt: 1 }} 
            onClose={() => setTestResult(null)}
            action={
              testResult.results && (
                <Button color="inherit" size="small" onClick={() => setShowResultsDialog(true)}>
                  View Details
                </Button>
              )
            }
          >
            {testResult.success ? testResult.message : testResult.error}
            {testResult.note && (
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                {testResult.note}
              </Typography>
            )}
          </Alert>
        )}

        <Dialog 
          open={showResultsDialog} 
          onClose={() => setShowResultsDialog(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>
            Test Results
            <Typography variant="subtitle2" color="text.secondary">
              {testResult?.passed}/{testResult?.total} Passed
            </Typography>
          </DialogTitle>
          <DialogContent dividers>
            {testResult?.results && (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Method</TableCell>
                      <TableCell>Path</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Code</TableCell>
                      <TableCell>Time</TableCell>
                      <TableCell>Response/Error</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {testResult.results.map((result: any, index: number) => (
                      <TableRow key={index} hover>
                        <TableCell>
                          <Chip 
                            label={result.method} 
                            size="small" 
                            variant="outlined"
                            color={
                              result.method === 'GET' ? 'success' :
                              result.method === 'POST' ? 'primary' :
                              'default'
                            }
                            sx={{ fontSize: '0.7rem', height: 20 }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {result.path}
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={result.status} 
                            color={result.status === 'pass' ? 'success' : 'error'} 
                            size="small" 
                            sx={{ height: 20 }}
                          />
                        </TableCell>
                        <TableCell>{result.statusCode || '-'}</TableCell>
                        <TableCell>{result.duration ? `${result.duration}ms` : '-'}</TableCell>
                        <TableCell sx={{ 
                          maxWidth: 400, 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis', 
                          whiteSpace: 'nowrap',
                          fontFamily: 'monospace',
                          fontSize: '0.8rem'
                        }}>
                          {result.error || (typeof result.response === 'string' ? result.response : JSON.stringify(result.response))}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowResultsDialog(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>

      {/* Scrollable Collections Area */}
      <Box sx={{ 
        flex: 1, 
        overflow: 'auto', 
        overflowX: 'hidden',
        px: 3, 
        py: 1, 
        minHeight: 0,
        maxHeight: '100%'
      }}>
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
                {collection.requestCount > 0 && (
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
            <AccordionDetails sx={{ p: 1 }}>
              {isLoadingRequests && (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              )}
              
              {collection.requests && (
                <List dense disablePadding>
                  {collection.requests.map((request) => (
                    <ListItem key={request.id} disablePadding>
                      <ListItemButton onClick={() => handleRequestToggle(request.id)} sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          <Checkbox
                            checked={selectedRequests.has(request.id)}
                            edge="start"
                            tabIndex={-1}
                            disableRipple
                            size="small"
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
                                sx={{ 
                                  minWidth: 50, 
                                  height: 20, 
                                  fontFamily: 'monospace', 
                                  fontSize: '0.65rem',
                                  '& .MuiChip-label': { px: 1 }
                                }}
                              />
                              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                {request.path}
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                              {request.name}
                            </Typography>
                          }
                          sx={{ my: 0 }}
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

