import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Refresh as RefreshIcon,
  BarChart as StatsIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  IconButton,
  TableSortLabel,
} from '@mui/material';
import React, { useState } from 'react';
import { useCoverage } from '../hooks/pages/useCoverage';

type SortField = 'category' | 'total' | 'covered' | 'coverage_percentage';
type SortOrder = 'asc' | 'desc';

const Coverage: React.FC = () => {
  const {
    coverageSummary,
    isLoadingSummary,
    summaryError,
    uncoveredRequirements,
    isLoadingUncovered,
    uncoveredError,
    filters,
    setFilters,
    refreshAll,
  } = useCoverage();

  const [sortField, setSortField] = useState<SortField>('coverage_percentage');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Get coverage color based on percentage
  const getCoverageColor = (percentage: number) => {
    if (percentage >= 80) return 'success';
    if (percentage >= 50) return 'warning';
    return 'error';
  };

  // Handle sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Sort category data
  const getSortedCategories = () => {
    if (!coverageSummary) return [];
    const entries = Object.entries(coverageSummary.by_category);
    return entries.sort((a, b) => {
      const [catA, dataA] = a;
      const [catB, dataB] = b;
      let comparison = 0;
      
      switch (sortField) {
        case 'category':
          comparison = catA.localeCompare(catB);
          break;
        case 'total':
          comparison = dataA.total - dataB.total;
          break;
        case 'covered':
          comparison = dataA.covered - dataB.covered;
          break;
        case 'coverage_percentage':
          comparison = dataA.coverage_percentage - dataB.coverage_percentage;
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  };

  // Calculate active filter count
  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length;

  return (
    <Box>
      {/* Header */}

      {/* Quick Stats */}
      <Box sx={{ mb: 1 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <StatsIcon color="primary" />
                <Typography variant="h6" sx={{ my: 0 }}>Coverage</Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Total Requirements</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {coverageSummary?.total_requirements || 0}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Coverage</Typography>
                  <Typography variant="body2" fontWeight="bold" color={
                    coverageSummary && coverageSummary.coverage_percentage !== undefined 
                      ? getCoverageColor(coverageSummary.coverage_percentage) + '.main' 
                      : 'text.primary'
                  }>
                    {(coverageSummary?.coverage_percentage ?? 0).toFixed(1)}%
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Categories</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {coverageSummary ? Object.keys(coverageSummary.by_category).length : 0}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Gaps</Typography>
                  <Typography variant="body2" fontWeight="bold" color="error.main">
                    {uncoveredRequirements.length}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Filters */}
      <Box sx={{ mb: 1, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={filters.category || ''}
            onChange={(e) => setFilters({ ...filters, category: e.target.value || undefined })}
            label="Category"
          >
            <MenuItem value="">All Categories</MenuItem>
            <MenuItem value="playback">Playback</MenuItem>
            <MenuItem value="auth">Authentication</MenuItem>
            <MenuItem value="navigation">Navigation</MenuItem>
            <MenuItem value="search">Search</MenuItem>
            <MenuItem value="ui">UI/UX</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Priority</InputLabel>
          <Select
            value={filters.priority || ''}
            onChange={(e) => setFilters({ ...filters, priority: e.target.value || undefined })}
            label="Priority"
          >
            <MenuItem value="">All Priorities</MenuItem>
            <MenuItem value="P1">P1 - Critical</MenuItem>
            <MenuItem value="P2">P2 - High</MenuItem>
            <MenuItem value="P3">P3 - Medium</MenuItem>
          </Select>
        </FormControl>
        {activeFilterCount > 0 && (
          <Chip 
            label={`${activeFilterCount} filter${activeFilterCount > 1 ? 's' : ''} active`}
            size="small"
            onDelete={() => setFilters({})}
            color="primary"
          />
        )}
        <Box sx={{ ml: 'auto' }}>
          <Tooltip title="Refresh data">
            <IconButton size="small" onClick={() => refreshAll()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Error Display */}
      {(summaryError || uncoveredError) && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {summaryError || uncoveredError}
        </Alert>
      )}

      {/* Loading State */}
      {isLoadingSummary && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Overall Coverage Summary */}
      {!isLoadingSummary && coverageSummary && (
        <>
          {/* Coverage by Category */}
          <Card sx={{ mb: 1 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6" sx={{ my: 0 }}>
                  Coverage by Category
                </Typography>
              </Box>
              <TableContainer>
                <Table size="small" sx={{ 
                  '& .MuiTableRow-root': { height: '40px' },
                  '& .MuiTableCell-root': { 
                    px: 1, 
                    py: 0.5,
                    fontSize: '0.875rem',
                  }
                }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ py: 1 }}>
                        <TableSortLabel
                          active={sortField === 'category'}
                          direction={sortField === 'category' ? sortOrder : 'asc'}
                          onClick={() => handleSort('category')}
                        >
                          <strong>Category</strong>
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 1 }}>
                        <Tooltip title="Total requirements in this category">
                          <TableSortLabel
                            active={sortField === 'total'}
                            direction={sortField === 'total' ? sortOrder : 'asc'}
                            onClick={() => handleSort('total')}
                          >
                            <strong>Total</strong>
                          </TableSortLabel>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 1 }}>
                        <Tooltip title="Requirements with test coverage">
                          <TableSortLabel
                            active={sortField === 'covered'}
                            direction={sortField === 'covered' ? sortOrder : 'asc'}
                            onClick={() => handleSort('covered')}
                          >
                            <strong>Covered</strong>
                          </TableSortLabel>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 1 }}>
                        <Tooltip title="Number of linked testcases">
                          <strong>Testcases</strong>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 1 }}>
                        <Tooltip title="Number of linked scripts">
                          <strong>Scripts</strong>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right" sx={{ py: 1 }}>
                        <Tooltip title="Coverage percentage (80%+ is excellent)">
                          <TableSortLabel
                            active={sortField === 'coverage_percentage'}
                            direction={sortField === 'coverage_percentage' ? sortOrder : 'asc'}
                            onClick={() => handleSort('coverage_percentage')}
                          >
                            <strong>Coverage %</strong>
                          </TableSortLabel>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right" sx={{ py: 1 }}>
                        <strong>Progress</strong>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {getSortedCategories().map(([category, data]) => (
                      <TableRow
                        key={category}
                        sx={{
                          '&:hover': {
                            backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                          },
                        }}
                      >
                        <TableCell sx={{ py: 0.5 }}>
                          <Chip label={category} size="small" />
                        </TableCell>
                        <TableCell align="center" sx={{ py: 0.5 }}>{data.total}</TableCell>
                        <TableCell align="center" sx={{ py: 0.5 }}>{data.covered}</TableCell>
                        <TableCell align="center" sx={{ py: 0.5 }}>{data.testcase_count}</TableCell>
                        <TableCell align="center" sx={{ py: 0.5 }}>{data.script_count}</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          <Typography
                            variant="body2"
                            fontWeight="medium"
                            color={
                              (data.coverage_percentage ?? 0) >= 80
                                ? 'success.main'
                                : (data.coverage_percentage ?? 0) >= 50
                                ? 'warning.main'
                                : 'error.main'
                            }
                          >
                            {(data.coverage_percentage ?? 0).toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ width: 150, py: 0.5 }}>
                          <LinearProgress
                            variant="determinate"
                            value={data.coverage_percentage ?? 0}
                            color={getCoverageColor(data.coverage_percentage ?? 0) as any}
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </>
      )}

      {/* Uncovered Requirements */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box display="flex" alignItems="center" gap={1}>
              <WarningIcon color="error" />
              <Typography variant="h6" sx={{ my: 0 }}>Uncovered Requirements</Typography>
            </Box>
            <Chip
              label={`${uncoveredRequirements.length} gap${uncoveredRequirements.length !== 1 ? 's' : ''}`}
              color="error"
              size="small"
            />
          </Box>

          {isLoadingUncovered && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
              <CircularProgress size={24} />
            </Box>
          )}

          {!isLoadingUncovered && uncoveredRequirements.length === 0 && (
            <Alert severity="success" icon={<CheckIcon />}>
              🎉 Excellent! All requirements have test coverage.
            </Alert>
          )}

          {!isLoadingUncovered && uncoveredRequirements.length > 0 && (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small" sx={{ 
                '& .MuiTableRow-root': { height: '40px' },
                '& .MuiTableCell-root': { 
                  px: 1, 
                  py: 0.5,
                  fontSize: '0.875rem',
                }
              }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ py: 1 }}><strong>Code</strong></TableCell>
                    <TableCell sx={{ py: 1 }}><strong>Name</strong></TableCell>
                    <TableCell sx={{ py: 1 }}><strong>Category</strong></TableCell>
                    <TableCell sx={{ py: 1 }}>
                      <Tooltip title="P1 = Critical, P2 = High, P3 = Medium">
                        <strong>Priority</strong>
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ py: 1 }}><strong>App Type</strong></TableCell>
                    <TableCell sx={{ py: 1 }}><strong>Device</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {uncoveredRequirements.map((req) => (
                    <TableRow
                      key={req.requirement_id}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                        },
                      }}
                    >
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
                          color={
                            req.priority === 'P1'
                              ? 'error'
                              : req.priority === 'P2'
                              ? 'warning'
                              : 'info'
                          }
                        />
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        <Typography variant="caption">{req.app_type}</Typography>
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        <Typography variant="caption">{req.device_model}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default Coverage;

