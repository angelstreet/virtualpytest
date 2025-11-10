import {
  Assignment as RequirementIcon,
  Add as AddIcon,
  Edit as EditIcon,
  FilterList as FilterIcon,
  Link as LinkIcon,
  Search as SearchIcon,
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
  Paper,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import React, { useState } from 'react';
import { useRequirements, Requirement } from '../hooks/pages/useRequirements';

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
  } = useRequirements();

  const [searchQuery, setSearchQuery] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<Requirement | null>(null);

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

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P1': return 'error';
      case 'P2': return 'warning';
      case 'P3': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Requirements Management
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Define, track, and link requirements to testcases and scripts for comprehensive coverage tracking.
        </Typography>
      </Box>

      {/* Actions Bar */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateOpen}
        >
          Create Requirement
        </Button>
        <Button
          variant="outlined"
          startIcon={<FilterIcon />}
          onClick={() => setFilters({})}
        >
          Clear Filters
        </Button>
      </Box>

      {/* Filters */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <TextField
            fullWidth
            size="small"
            label="Search"
            placeholder="Code, name, description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
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
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
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
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
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
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth size="small">
            <InputLabel>Device Model</InputLabel>
            <Select
              value={filters.device_model || ''}
              onChange={(e) => setFilters({ ...filters, device_model: e.target.value || undefined })}
              label="Device Model"
            >
              <MenuItem value="">All</MenuItem>
              {deviceModels.map(model => (
                <MenuItem key={model} value={model}>{model}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>

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
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Code</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>App Type</TableCell>
                <TableCell>Device</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRequirements.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                      No requirements found. Create your first requirement to get started.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredRequirements.map((req) => (
                  <TableRow key={req.requirement_id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {req.requirement_code}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{req.requirement_name}</Typography>
                      {req.description && (
                        <Typography variant="caption" color="textSecondary" display="block">
                          {req.description.substring(0, 60)}
                          {req.description.length > 60 ? '...' : ''}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label={req.category || 'none'} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={req.priority}
                        size="small"
                        color={getPriorityColor(req.priority) as any}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{req.app_type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{req.device_model}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={req.status}
                        size="small"
                        color={req.status === 'active' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleEditOpen(req)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
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
    </Box>
  );
};

export default Requirements;

