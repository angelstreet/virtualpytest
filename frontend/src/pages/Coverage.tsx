import {
  Assessment as CoverageIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  TrendingUp as TrendingUpIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
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
  Button,
} from '@mui/material';
import React from 'react';
import { useCoverage } from '../hooks/pages/useCoverage';

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

  // Get coverage color based on percentage
  const getCoverageColor = (percentage: number) => {
    if (percentage >= 80) return 'success';
    if (percentage >= 50) return 'warning';
    return 'error';
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Requirements Coverage
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Track test coverage across all requirements and identify gaps in testing.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<FilterIcon />} onClick={() => refreshAll()}>
          Refresh
        </Button>
      </Box>

      {/* Filters */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth size="small">
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
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth size="small">
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
        </Grid>
      </Grid>

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
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {/* Total Coverage Card */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <CoverageIcon color="primary" />
                      <Typography variant="h6">Overall Coverage</Typography>
                    </Box>
                  </Box>
                  <Typography variant="h3" color="primary" gutterBottom>
                    {coverageSummary.coverage_percentage.toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={coverageSummary.coverage_percentage}
                    color={getCoverageColor(coverageSummary.coverage_percentage) as any}
                    sx={{ height: 8, borderRadius: 4, mb: 2 }}
                  />
                  <Typography variant="body2" color="textSecondary">
                    {coverageSummary.total_covered} of {coverageSummary.total_requirements} requirements covered
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Covered Requirements Card */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <CheckIcon color="success" />
                      <Typography variant="h6">Covered</Typography>
                    </Box>
                  </Box>
                  <Typography variant="h3" color="success.main" gutterBottom>
                    {coverageSummary.total_covered}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Requirements with at least one testcase or script
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Uncovered Requirements Card */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <WarningIcon color="error" />
                      <Typography variant="h6">Uncovered</Typography>
                    </Box>
                  </Box>
                  <Typography variant="h3" color="error.main" gutterBottom>
                    {coverageSummary.total_requirements - coverageSummary.total_covered}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Requirements without any coverage
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Coverage by Category */}
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Coverage by Category
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Category</TableCell>
                      <TableCell align="center">Total</TableCell>
                      <TableCell align="center">Covered</TableCell>
                      <TableCell align="center">Testcases</TableCell>
                      <TableCell align="center">Scripts</TableCell>
                      <TableCell align="right">Coverage %</TableCell>
                      <TableCell align="right">Progress</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(coverageSummary.by_category).map(([category, data]) => (
                      <TableRow key={category} hover>
                        <TableCell>
                          <Chip label={category} size="small" />
                        </TableCell>
                        <TableCell align="center">{data.total}</TableCell>
                        <TableCell align="center">{data.covered}</TableCell>
                        <TableCell align="center">{data.testcase_count}</TableCell>
                        <TableCell align="center">{data.script_count}</TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            fontWeight="medium"
                            color={
                              data.coverage_percentage >= 80
                                ? 'success.main'
                                : data.coverage_percentage >= 50
                                ? 'warning.main'
                                : 'error.main'
                            }
                          >
                            {data.coverage_percentage.toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ width: 150 }}>
                          <LinearProgress
                            variant="determinate"
                            value={data.coverage_percentage}
                            color={getCoverageColor(data.coverage_percentage) as any}
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
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Box display="flex" alignItems="center" gap={1}>
              <WarningIcon color="error" />
              <Typography variant="h6">Uncovered Requirements</Typography>
            </Box>
            <Chip
              label={`${uncoveredRequirements.length} gaps`}
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
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Code</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Priority</TableCell>
                    <TableCell>App Type</TableCell>
                    <TableCell>Device</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {uncoveredRequirements.map((req) => (
                    <TableRow key={req.requirement_id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {req.requirement_code}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{req.requirement_name}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={req.category || 'none'} size="small" />
                      </TableCell>
                      <TableCell>
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
                      <TableCell>
                        <Typography variant="caption">{req.app_type}</Typography>
                      </TableCell>
                      <TableCell>
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

      {/* Summary Stats */}
      {coverageSummary && (
        <Box sx={{ mt: 3, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Typography variant="caption" color="textSecondary" display="block">
            💡 <strong>Tip:</strong> Focus on P1 (Critical) uncovered requirements first. Link testcases
            and scripts to requirements from the Requirements page to improve coverage.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default Coverage;

