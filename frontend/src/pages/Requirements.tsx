import {
  Add as AddIcon,
  Edit as EditIcon,
  Link as LinkIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandIcon,
  BarChart as StatsIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorCircleIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  InputAdornment,
} from '@mui/material';
import React, { useState } from 'react';
import { useRequirements, Requirement } from '../hooks/pages/useRequirements';
import { RequirementCoverageModal } from '../components/requirements/RequirementCoverageModal';
import { LinkTestcasePickerModal } from '../components/requirements/LinkTestcasePickerModal';

const Requirements: React.FC = () => {
  const {
    requirements,
    isLoading,
    error,
    createRequirement,
    updateRequirement,
    filters,
    setFilters,
    categories,
    priorities,
    appTypes,
    deviceModels,
    refreshRequirements,
    getRequirementCoverage,
    getAvailableTestcases,
    linkMultipleTestcases,
    unlinkTestcase,
    coverageCounts,
  } = useRequirements();

  const [searchQuery, setSearchQuery] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<Requirement | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  
  // Coverage modal state
  const [coverageModalOpen, setCoverageModalOpen] = useState(false);
  const [coverageRequirement, setCoverageRequirement] = useState<{ id: string; code: string; name: string } | null>(null);
  
  // Link testcase picker modal state
  const [linkPickerOpen, setLinkPickerOpen] = useState(false);
  const [linkRequirement, setLinkRequirement] = useState<{ id: string; code: string; name: string } | null>(null);

  // Create/Edit form state
  const [formData, setFormData] = useState({
    requirement_code: '',
    requirement_name: '',
    category: '',
    priority: 'P2',
    description: '',
    acceptance_criteria: [] as string[],
    app_type: 'all',
    device_model: 'all',
    status: 'active',
  });

  const handleCreateOpen = () => {
    setFormData({
      requirement_code: '',
      requirement_name: '',
      category: '',
      priority: 'P2',
      description: '',
      acceptance_criteria: [],
      app_type: 'all',
      device_model: 'all',
      status: 'active',
    });
    setCreateDialogOpen(true);
  };

  const handleEditOpen = (requirement: Requirement) => {
    setSelectedRequirement(requirement);
    setFormData({
      requirement_code: requirement.requirement_code,
      requirement_name: requirement.requirement_name,
      category: requirement.category || '',
      priority: requirement.priority,
      description: requirement.description || '',
      acceptance_criteria: requirement.acceptance_criteria || [],
      app_type: requirement.app_type,
      device_model: requirement.device_model,
      status: requirement.status,
    });
    setEditDialogOpen(true);
  };

  const handleCreate = async () => {
    const result = await createRequirement(formData);
    if (result.success) {
      setCreateDialogOpen(false);
      refreshRequirements();
    } else {
      alert(`Error: ${result.error}`);
    }
  };

  const handleEdit = async () => {
    if (!selectedRequirement) return;
    const result = await updateRequirement(selectedRequirement.requirement_id, formData);
    if (result.success) {
      setEditDialogOpen(false);
      refreshRequirements();
    } else {
      alert(`Error: ${result.error}`);
    }
  };

  // Filter requirements by search query
  const filteredRequirements = requirements.filter(req => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      req.requirement_code.toLowerCase().includes(query) ||
      req.requirement_name.toLowerCase().includes(query) ||
      (req.description && req.description.toLowerCase().includes(query))
    );
  });

  // Calculate active filter count
  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length;

  // Calculate stats
  const totalReqs = requirements.length;
  const p1Count = requirements.filter(r => r.priority === 'P1').length;
  const p2Count = requirements.filter(r => r.priority === 'P2').length;
  const p3Count = requirements.filter(r => r.priority === 'P3').length;
  const activeCount = requirements.filter(r => r.status === 'active').length;

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P1': return 'error';
      case 'P2': return 'warning';
      case 'P3': return 'info';
      default: return 'default';
    }
  };

  // Toggle row expansion
  const toggleRowExpansion = (requirementId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(requirementId)) {
        newSet.delete(requirementId);
      } else {
        newSet.add(requirementId);
      }
      return newSet;
    });
  };

  // Open coverage modal
  const handleOpenCoverage = (req: Requirement) => {
    setCoverageRequirement({
      id: req.requirement_id,
      code: req.requirement_code,
      name: req.requirement_name,
    });
    setCoverageModalOpen(true);
  };

  // Open link testcase picker from coverage modal
  const handleOpenLinkPickerFromCoverage = () => {
    if (coverageRequirement) {
      setLinkRequirement(coverageRequirement);
      setCoverageModalOpen(false);
      setLinkPickerOpen(true);
    }
  };

  // Open link testcase picker directly
  const handleOpenLinkPicker = (req: Requirement) => {
    setLinkRequirement({
      id: req.requirement_id,
      code: req.requirement_code,
      name: req.requirement_name,
    });
    setLinkPickerOpen(true);
  };

  // Get coverage badge for a requirement
  const getCoverageBadge = (requirementId: string) => {
    const coverage = coverageCounts[requirementId];
    if (!coverage) {
      return { icon: <ErrorCircleIcon />, color: 'error' as const, text: '0 tests' };
    }

    const totalCount = coverage.total_count;
    if (totalCount === 0) {
      return { icon: <ErrorCircleIcon />, color: 'error' as const, text: '0 tests' };
    }
    if (totalCount >= 3) {
      return { icon: <CheckCircleIcon />, color: 'success' as const, text: `${totalCount} tests` };
    }
    return { icon: <WarningIcon />, color: 'warning' as const, text: `${totalCount} test${totalCount !== 1 ? 's' : ''}` };
  };

  return (
    <Box>
      {/* Quick Stats */}
      <Box sx={{ mb: 1 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <StatsIcon color="primary" />
                <Typography variant="h6" sx={{ my: 0 }}>Requirements</Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Total</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {totalReqs}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Active</Typography>
                  <Typography variant="body2" fontWeight="bold" color="success.main">
                    {activeCount}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Tooltip title="Critical priority">
                    <Chip label={`P1: ${p1Count}`} size="small" color="error" />
                  </Tooltip>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Tooltip title="High priority">
                    <Chip label={`P2: ${p2Count}`} size="small" color="warning" />
                  </Tooltip>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Tooltip title="Medium priority">
                    <Chip label={`P3: ${p3Count}`} size="small" color="info" />
                  </Tooltip>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Actions Bar & Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 1, flexWrap: 'wrap', alignItems: 'center' }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateOpen}
          size="small"
        >
          Create Requirement
        </Button>
        <TextField
          size="small"
          placeholder="Search requirements..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ minWidth: 250 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchQuery && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchQuery('')}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={filters.category || ''}
            onChange={(e) => setFilters({ ...filters, category: e.target.value || undefined })}
            label="Category"
          >
            <MenuItem value="">All</MenuItem>
            {categories.map(cat => (
              <MenuItem key={cat} value={cat}>{cat}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Priority</InputLabel>
          <Select
            value={filters.priority || ''}
            onChange={(e) => setFilters({ ...filters, priority: e.target.value || undefined })}
            label="Priority"
          >
            <MenuItem value="">All</MenuItem>
            {priorities.map(pri => (
              <MenuItem key={pri} value={pri}>{pri}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>App Type</InputLabel>
          <Select
            value={filters.app_type || ''}
            onChange={(e) => setFilters({ ...filters, app_type: e.target.value || undefined })}
            label="App Type"
          >
            <MenuItem value="">All</MenuItem>
            {appTypes.map(type => (
              <MenuItem key={type} value={type}>{type}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Device</InputLabel>
          <Select
            value={filters.device_model || ''}
            onChange={(e) => setFilters({ ...filters, device_model: e.target.value || undefined })}
            label="Device"
          >
            <MenuItem value="">All</MenuItem>
            {deviceModels.map(model => (
              <MenuItem key={model} value={model}>{model}</MenuItem>
            ))}
          </Select>
        </FormControl>
        {activeFilterCount > 0 && (
          <Chip 
            label={`${activeFilterCount} filter${activeFilterCount > 1 ? 's' : ''}`}
            size="small"
            onDelete={() => setFilters({})}
            color="primary"
          />
        )}
        <Box sx={{ ml: 'auto' }}>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={() => refreshRequirements()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Results count */}
      {searchQuery && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" color="textSecondary">
            Showing {filteredRequirements.length} of {totalReqs} requirement{totalReqs !== 1 ? 's' : ''}
          </Typography>
        </Box>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Requirements Table */}
      {!isLoading && (
        <Card>
          <CardContent>
            <TableContainer>
              <Table size="small" sx={{ 
                '& .MuiTableRow-root': { height: '40px' },
                '& .MuiTableCell-root': { 
                  px: 1, 
                  py: 0.5,
                  fontSize: '0.875rem',
                  whiteSpace: 'nowrap',
                }
              }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ py: 1, width: 40 }}></TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>Code</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>Name</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>Category</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <Tooltip title="P1 = Critical, P2 = High, P3 = Medium">
                        <strong>Priority</strong>
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>App Type</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>Device</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <Tooltip title="Test coverage status">
                        <strong>Coverage</strong>
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <strong>Status</strong>
                    </TableCell>
                    <TableCell sx={{ py: 1 }} align="right">
                      <strong>Actions</strong>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredRequirements.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center">
                        <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                          {searchQuery 
                            ? `No requirements found matching "${searchQuery}"`
                            : 'No requirements found. Create your first requirement to get started.'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredRequirements.map((req) => (
                      <React.Fragment key={req.requirement_id}>
                        <TableRow
                          sx={{
                            '&:hover': {
                              backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                            },
                          }}
                        >
                          <TableCell sx={{ py: 0.5 }}>
                            <IconButton 
                              size="small" 
                              onClick={() => toggleRowExpansion(req.requirement_id)}
                              sx={{ p: 0 }}
                            >
                              <ExpandIcon 
                                fontSize="small" 
                                sx={{ 
                                  transform: expandedRows.has(req.requirement_id) ? 'rotate(180deg)' : 'rotate(0deg)',
                                  transition: 'transform 0.2s'
                                }}
                              />
                            </IconButton>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Typography variant="body2" fontWeight="medium">
                              {req.requirement_code}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Typography variant="body2">{req.requirement_name}</Typography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Chip label={req.category || 'none'} size="small" />
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Chip
                              label={req.priority}
                              size="small"
                              color={getPriorityColor(req.priority) as any}
                            />
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Typography variant="caption">{req.app_type}</Typography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Typography variant="caption">{req.device_model}</Typography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Tooltip title="Click to view coverage details">
                              <Chip
                                icon={getCoverageBadge(req.requirement_id).icon}
                                label={getCoverageBadge(req.requirement_id).text}
                                size="small"
                                color={getCoverageBadge(req.requirement_id).color}
                                onClick={() => handleOpenCoverage(req)}
                                sx={{ cursor: 'pointer' }}
                              />
                            </Tooltip>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Chip
                              label={req.status}
                              size="small"
                              color={req.status === 'active' ? 'success' : 'default'}
                            />
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }} align="right">
                            <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                              <Tooltip title="Edit requirement">
                                <IconButton size="small" onClick={() => handleEditOpen(req)} sx={{ p: 0.5 }}>
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Link testcases">
                                <IconButton size="small" onClick={() => handleOpenLinkPicker(req)} sx={{ p: 0.5 }}>
                                  <LinkIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                        {/* Expanded row details */}
                        {expandedRows.has(req.requirement_id) && (
                          <TableRow
                            sx={{
                              '&:hover': {
                                backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                              },
                            }}
                          >
                            <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={10}>
                              <Box sx={{ py: 1, px: 2, bgcolor: 'rgba(0, 0, 0, 0.02)' }}>
                                {req.description && (
                                  <Box sx={{ mb: 1 }}>
                                    <Typography variant="caption" color="textSecondary" fontWeight="bold">
                                      Description:
                                    </Typography>
                                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                                      {req.description}
                                    </Typography>
                                  </Box>
                                )}
                                {req.acceptance_criteria && (Array.isArray(req.acceptance_criteria) ? req.acceptance_criteria.length > 0 : req.acceptance_criteria) && (
                                  <Box>
                                    <Typography variant="caption" color="textSecondary" fontWeight="bold">
                                      Acceptance Criteria:
                                    </Typography>
                                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                                      {Array.isArray(req.acceptance_criteria) 
                                        ? req.acceptance_criteria.join(', ')
                                        : req.acceptance_criteria}
                                    </Typography>
                                  </Box>
                                )}
                                {!req.description && (!req.acceptance_criteria || req.acceptance_criteria.length === 0) && (
                                  <Typography variant="caption" color="textSecondary" fontStyle="italic">
                                    No additional details available
                                  </Typography>
                                )}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Requirement</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Requirement Code"
                placeholder="REQ_PLAYBACK_001"
                value={formData.requirement_code}
                onChange={(e) => setFormData({ ...formData, requirement_code: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Requirement Name"
                placeholder="Basic Video Playback"
                value={formData.requirement_name}
                onChange={(e) => setFormData({ ...formData, requirement_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  label="Category"
                >
                  {categories.map(cat => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  label="Priority"
                >
                  {priorities.map(pri => (
                    <MenuItem key={pri} value={pri}>{pri}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  label="Status"
                >
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="deprecated">Deprecated</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>App Type</InputLabel>
                <Select
                  value={formData.app_type}
                  onChange={(e) => setFormData({ ...formData, app_type: e.target.value })}
                  label="App Type"
                >
                  {appTypes.map(type => (
                    <MenuItem key={type} value={type}>{type}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Device Model</InputLabel>
                <Select
                  value={formData.device_model}
                  onChange={(e) => setFormData({ ...formData, device_model: e.target.value })}
                  label="Device Model"
                >
                  {deviceModels.map(model => (
                    <MenuItem key={model} value={model}>{model}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Requirement</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Requirement Code"
                value={formData.requirement_code}
                disabled
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Requirement Name"
                value={formData.requirement_name}
                onChange={(e) => setFormData({ ...formData, requirement_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  label="Priority"
                >
                  {priorities.map(pri => (
                    <MenuItem key={pri} value={pri}>{pri}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  label="Status"
                >
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="deprecated">Deprecated</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Coverage Modal */}
      {coverageRequirement && (
        <RequirementCoverageModal
          open={coverageModalOpen}
          onClose={() => setCoverageModalOpen(false)}
          requirementId={coverageRequirement.id}
          requirementCode={coverageRequirement.code}
          requirementName={coverageRequirement.name}
          getCoverage={getRequirementCoverage}
          onUnlinkTestcase={unlinkTestcase}
          onOpenLinkDialog={handleOpenLinkPickerFromCoverage}
        />
      )}

      {/* Link Testcase Picker Modal */}
      {linkRequirement && (
        <LinkTestcasePickerModal
          open={linkPickerOpen}
          onClose={() => setLinkPickerOpen(false)}
          requirementId={linkRequirement.id}
          requirementCode={linkRequirement.code}
          requirementName={linkRequirement.name}
          getAvailableTestcases={getAvailableTestcases}
          onLinkTestcases={linkMultipleTestcases}
          onSuccess={() => {
            refreshRequirements();
            // Reopen coverage modal if it was open
            if (coverageRequirement) {
              setCoverageModalOpen(true);
            }
          }}
        />
      )}
    </Box>
  );
};

export default Requirements;

