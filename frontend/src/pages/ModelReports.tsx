import {
  Memory as ModelIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  PlayArrow as ActionIcon,
  Visibility as VerificationIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useExecutionResults, ExecutionResult } from '../hooks/pages/useExecutionResults';
import { useUserInterface } from '../hooks/pages/useUserInterface';
import { useMetrics } from '../hooks/navigation/useMetrics';

type FilterType = 'all' | 'action' | 'verification';

const ModelReports: React.FC = () => {
  const { getAllExecutionResults } = useExecutionResults();
  const { getAllUserInterfaces } = useUserInterface();
  const metricsHook = useMetrics();
  const [executionResults, setExecutionResults] = useState<ExecutionResult[]>([]);
  const [userInterfaces, setUserInterfaces] = useState<any[]>([]);
  const [selectedUserInterface, setSelectedUserInterface] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [treeToInterfaceMap, setTreeToInterfaceMap] = useState<Record<string, string>>({});
  const [treeToNameMap, setTreeToNameMap] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState<FilterType>('all');

  // Load execution results and user interfaces on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load user interfaces first
        const interfaces = await getAllUserInterfaces();

        // Create mapping from tree_id to userinterface_name
        const treeToUIMap: Record<string, string> = {};
        const treeNameMap: Record<string, string> = {};
        
        interfaces.forEach((ui) => {
          if (ui.root_tree?.id) {
            treeToUIMap[ui.root_tree.id] = ui.name;
            treeNameMap[ui.root_tree.id] = ui.root_tree.name || 'Root Tree';
          }
          // Also map any nested trees if they exist (cast to any to handle potential nested_trees)
          const uiWithNested = ui as any;
          if (uiWithNested.nested_trees && Array.isArray(uiWithNested.nested_trees)) {
            uiWithNested.nested_trees.forEach((nestedTree: any) => {
              if (nestedTree.id) {
                treeToUIMap[nestedTree.id] = ui.name;
                treeNameMap[nestedTree.id] = nestedTree.name || 'Nested Tree';
              }
            });
          }
        });

        setUserInterfaces(interfaces);
        setTreeToInterfaceMap(treeToUIMap);
        setTreeToNameMap(treeNameMap);
        
        // Don't auto-select - let user choose explicitly to avoid race conditions
      } catch (err) {
        console.error('[@component:ModelReports] Error loading data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []); // Only run once on mount

  // Load execution results and metrics when user interface changes
  useEffect(() => {
    const loadExecutionResultsForInterface = async () => {
      if (!selectedUserInterface || userInterfaces.length === 0 || Object.keys(treeToInterfaceMap).length === 0) {
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        
        const selectedUI = userInterfaces.find(ui => ui.name === selectedUserInterface);
        if (selectedUI?.root_tree?.id) {
          console.log(`[@ModelReports] Loading data for interface: ${selectedUserInterface}, tree: ${selectedUI.root_tree.id}`);
          
          // Load execution results for this specific tree only
          const results = await getAllExecutionResults();
          // Filter results by tree_id to reduce processing
          const filteredResults = results.filter(result => 
            treeToInterfaceMap[result.tree_id] === selectedUserInterface
          );
          
          console.log(`[@ModelReports] Filtered ${results.length} results to ${filteredResults.length} for interface ${selectedUserInterface}`);
          setExecutionResults(filteredResults);
          
          // Load metrics for this tree
          metricsHook.fetchMetrics(selectedUI.root_tree.id);
        }
      } catch (err) {
        console.error('[@component:ModelReports] Error loading execution results:', err);
        setError(err instanceof Error ? err.message : 'Failed to load execution results');
      } finally {
        setLoading(false);
      }
    };

    // Only run if we have all the necessary data
    if (selectedUserInterface && userInterfaces.length > 0 && Object.keys(treeToInterfaceMap).length > 0) {
      loadExecutionResultsForInterface();
    }
  }, [selectedUserInterface, userInterfaces, treeToInterfaceMap]);

  // Filter execution results based on execution type only (user interface already filtered)
  const filteredResults = executionResults.filter((result) => {
    // Filter by execution type
    if (filter === 'all') return true;
    return result.execution_type === filter;
  });

  // Calculate stats based on filtered results
  const totalExecutions = filteredResults.length;
  const passedExecutions = filteredResults.filter((result) => result.success).length;
  const successRate =
    totalExecutions > 0 ? ((passedExecutions / totalExecutions) * 100).toFixed(1) : 'N/A';

  // Calculate this week's executions (last 7 days)
  const oneWeekAgo = new Date();
  oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
  const thisWeekExecutions = filteredResults.filter(
    (result) => new Date(result.executed_at) >= oneWeekAgo,
  ).length;

  // Calculate average duration
  const avgDuration =
    totalExecutions > 0
      ? formatDuration(
          filteredResults.reduce((sum, result) => sum + result.execution_time_ms, 0) /
            totalExecutions,
        )
      : 'N/A';

  // Separate by execution type (for current interface stats)
  const actionExecutions = executionResults.filter((result) => result.execution_type === 'action');
  const verificationExecutions = executionResults.filter(
    (result) => result.execution_type === 'verification',
  );

  // Handle filter change
  const handleFilterChange = (_event: React.MouseEvent<HTMLElement>, newFilter: FilterType) => {
    if (newFilter !== null) {
      setFilter(newFilter);
    }
  };

  // Handle user interface selection change
  const handleUserInterfaceChange = (event: SelectChangeEvent) => {
    setSelectedUserInterface(event.target.value);
  };

  // Format duration helper
  function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(1);
    return `${minutes}m ${seconds}s`;
  }

  // Format date helper
  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  // Loading state component
  const LoadingState = () => (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
      <CircularProgress />
    </Box>
  );


  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h4" gutterBottom>
          Model Analysis Reports
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Analyze model performance by user interface - view confidence scores, success rates, and execution volumes for nodes and edges
        </Typography>
        
        {/* User Interface Selector */}
        <FormControl size="small" sx={{ minWidth: 250 }}>
          <InputLabel>Select User Interface</InputLabel>
          <Select
            value={selectedUserInterface}
            label="Select User Interface"
            onChange={handleUserInterfaceChange}
            disabled={userInterfaces.length === 0}
            displayEmpty
            renderValue={(value) => {
              if (!value) {
                return (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, fontStyle: 'italic', opacity: 0.6 }}>
                    <ModelIcon fontSize="small" />
                    Select user interface...
                  </Box>
                );
              }
              return (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ModelIcon fontSize="small" />
                  {value}
                </Box>
              );
            }}
          >
            <MenuItem value="">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, fontStyle: 'italic', opacity: 0.6 }}>
                <ModelIcon fontSize="small" />
                Select a user interface to analyze...
              </Box>
            </MenuItem>
            {userInterfaces.map((ui) => (
              <MenuItem key={ui.id} value={ui.name}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ModelIcon fontSize="small" />
                  {ui.name}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Show content only when user interface is selected */}
      {!selectedUserInterface ? (
        <Card>
          <CardContent sx={{ py: 8, textAlign: 'center' }}>
            <ModelIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Select User Interface to Analyze
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose a user interface from the dropdown above to view model performance metrics, 
              confidence scores, and execution data for nodes and edges.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Quick Stats */}
          <Box sx={{ mb: 0.5 }}>
            <Card>
              <CardContent sx={{ py: 0.5 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box display="flex" alignItems="center" gap={1}>
                    <ModelIcon color="primary" />
                    <Typography variant="h6">Execution Stats</Typography>
                    <Chip
                      label={selectedUserInterface}
                      size="small"
                      variant="outlined"
                      color="primary"
                    />
                  </Box>

              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">
                    {filter === 'all' ? 'Total Executions' : 'Filtered Executions'}
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {totalExecutions}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">This Week</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {thisWeekExecutions}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Success Rate</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {successRate}%
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Avg Duration</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {avgDuration}
                  </Typography>
                </Box>
                {filter === 'all' && (
                  <>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2">Edges</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {actionExecutions.length}
                      </Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2">Nodes</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {verificationExecutions.length}
                      </Typography>
                    </Box>
                  </>
                )}
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Recent Execution Results */}
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
            <Typography variant="h6">Recent Execution Results</Typography>

            {/* Filter Toggle Buttons */}
            <Box display="flex" alignItems="center" gap={1}>
              <FilterIcon fontSize="small" color="action" />
              <ToggleButtonGroup
                value={filter}
                exclusive
                onChange={handleFilterChange}
                size="small"
                aria-label="execution type filter"
              >
                <ToggleButton value="all" aria-label="all executions">
                  All
                </ToggleButton>
                <ToggleButton value="action" aria-label="edge executions">
                  <ActionIcon fontSize="small" sx={{ mr: 0.5 }} />
                  Edges
                </ToggleButton>
                <ToggleButton value="verification" aria-label="node executions">
                  <VerificationIcon fontSize="small" sx={{ mr: 0.5 }} />
                  Nodes
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>
          </Box>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small" sx={{ '& .MuiTableRow-root': { height: '40px' } }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Type</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>User Interface</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Name</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Success</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Volume</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Avg Duration</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Confidence</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Executed</strong>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <LoadingState />
                    </TableCell>
                  </TableRow>
                ) : filteredResults.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="textSecondary">
                        {filter === 'all'
                          ? 'No execution results available yet'
                          : `No ${filter === 'action' ? 'edge' : 'node'} execution results available yet`}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredResults.map((result) => {
                    // Get metrics for this element
                    const isAction = result.execution_type === 'action';
                    const elementId = isAction ? result.edge_id : result.node_id;
                    const metrics = isAction 
                      ? metricsHook.getEdgeMetrics(elementId || '') 
                      : metricsHook.getNodeMetrics(elementId || '');
                    
                    return (
                      <TableRow
                        key={result.id}
                        sx={{
                          '&:hover': {
                            backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                          },
                        }}
                      >
                        <TableCell sx={{ py: 0.5 }}>
                          <Chip
                            icon={
                              result.execution_type === 'action' ? (
                                <ActionIcon />
                              ) : (
                                <VerificationIcon />
                              )
                            }
                            label={result.execution_type === 'action' ? 'Edge' : 'Node'}
                            size="small"
                            variant="outlined"
                            color={result.execution_type === 'action' ? 'primary' : 'secondary'}
                          />
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          {treeToInterfaceMap[result.tree_id] || 'Unknown'}
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>{result.element_name}</TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          <Typography variant="body2" sx={{ 
                            color: metrics?.volume === 0 ? '#666' : 
                                   (metrics?.success_rate || 0) >= 0.8 ? 'success.main' : 
                                   (metrics?.success_rate || 0) >= 0.5 ? 'warning.main' : 'error.main'
                          }}>
                            {metrics?.volume === 0 ? 'N/A' : `${((metrics?.success_rate || 0) * 100).toFixed(0)}%`}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          <Typography variant="body2">
                            {metrics?.volume || 0}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          <Typography variant="body2">
                            {metrics?.avg_execution_time ? formatDuration(metrics.avg_execution_time) : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                fontWeight: 'bold',
                                fontSize: '0.9rem',
                                color: metrics?.volume === 0 ? '#666' : 
                                       (metrics?.confidence || 0) >= 0.7 ? 'success.main' : 
                                       (metrics?.confidence || 0) >= 0.5 ? 'warning.main' : 'error.main'
                              }}
                            >
                              {metrics?.volume === 0 ? 'N/A' : `${metrics?.confidence ? Math.round(metrics.confidence * 10) : 0}/10`}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>
                          {(() => {
                            // Show status based on metrics, not individual execution result
                            if (metrics?.volume === 0) {
                              return (
                                <Chip
                                  label="UNTESTED"
                                  color="default"
                                  size="small"
                                  variant="outlined"
                                  sx={{ color: '#666' }}
                                />
                              );
                            }
                            
                            // Show status based on success rate for tested elements
                            const successRate = metrics?.success_rate || 0;
                            if (successRate >= 0.8) {
                              return (
                                <Chip
                                  icon={<PassIcon />}
                                  label="GOOD"
                                  color="success"
                                  size="small"
                                />
                              );
                            } else if (successRate >= 0.5) {
                              return (
                                <Chip
                                  label="MIXED"
                                  color="warning"
                                  size="small"
                                />
                              );
                            } else {
                              return (
                                <Chip
                                  icon={<FailIcon />}
                                  label="POOR"
                                  color="error"
                                  size="small"
                                />
                              );
                            }
                          })()}
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>{formatDate(result.executed_at)}</TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      </>
      )}
    </Box>
  );
};

export default ModelReports;
