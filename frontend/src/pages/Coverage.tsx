/**
 * Coverage Dashboard Page
 * 
 * Central view showing requirements-testcases mapping with:
 * - Filter by userinterface
 * - View requirements and their linked testcases
 * - Click to open requirement or testcase details
 * - Simple, clean layout
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  Button,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  OpenInNew as OpenInNewIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  BarChart as StatsIcon,
} from '@mui/icons-material';
import { useRequirements } from '../hooks/pages/useRequirements';
import { RequirementCoverageModal } from '../components/requirements/RequirementCoverageModal';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface CoverageByUI {
  [ui: string]: Array<{
    requirement_id: string;
    requirement_code: string;
    requirement_name: string;
    priority: string;
    category: string;
    testcase_count: number;
    pass_rate: number;
  }>;
}

const Coverage: React.FC = () => {
  const {
    requirements,
    isLoading,
    refreshRequirements,
    getRequirementCoverage,
    unlinkTestcase,
    coverageCounts,
  } = useRequirements();

  const [selectedUI, setSelectedUI] = useState<string>('all');
  const [coverageByUI, setCoverageByUI] = useState<CoverageByUI>({});
  const [availableUIs, setAvailableUIs] = useState<string[]>([]);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  
  // Coverage modal state
  const [coverageModalOpen, setCoverageModalOpen] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<{ id: string; code: string; name: string } | null>(null);

  // Load userinterfaces
  useEffect(() => {
    loadUserInterfaces();
  }, []);

  // Group requirements by UI when data changes
  useEffect(() => {
    if (requirements.length > 0) {
      groupRequirementsByUI();
    }
  }, [requirements, coverageCounts]);

  const loadUserInterfaces = async () => {
    try {
      const url = buildServerUrl('/server/userinterface/list');
      const response = await fetch(url);
      const data = await response.json();
      
      if (data.success && data.userinterfaces) {
        const uiNames = data.userinterfaces.map((ui: any) => ui.userinterface_name);
        setAvailableUIs(uiNames);
      }
    } catch (err) {
      console.error('Error loading userinterfaces:', err);
    }
  };

  const groupRequirementsByUI = async () => {
    // For each requirement, get its coverage and group by UI
    const grouped: CoverageByUI = {};

    for (const req of requirements) {
      const coverage = coverageCounts[req.requirement_id];
      if (!coverage || coverage.total_count === 0) continue;

      // Get detailed coverage to find UIs
      try {
        const detailedCoverage = await getRequirementCoverage(req.requirement_id);
        if (!detailedCoverage) continue;

        const uiNames = Object.keys(detailedCoverage.testcases_by_ui);
        
        for (const uiName of uiNames) {
          if (!grouped[uiName]) {
            grouped[uiName] = [];
          }

          const uiTestcases = detailedCoverage.testcases_by_ui[uiName];
          const totalRuns = uiTestcases.reduce((sum, tc) => sum + tc.execution_count, 0);
          const totalPasses = uiTestcases.reduce((sum, tc) => sum + tc.pass_count, 0);
          const passRate = totalRuns > 0 ? totalPasses / totalRuns : 0;

          grouped[uiName].push({
            requirement_id: req.requirement_id,
            requirement_code: req.requirement_code,
            requirement_name: req.requirement_name,
            priority: req.priority,
            category: req.category || 'uncategorized',
            testcase_count: uiTestcases.length,
            pass_rate: passRate,
          });
        }
      } catch (err) {
        console.error(`Error loading coverage for ${req.requirement_code}:`, err);
      }
    }

    setCoverageByUI(grouped);
  };

  const handleOpenRequirement = (reqId: string, reqCode: string, reqName: string) => {
    setSelectedRequirement({ id: reqId, code: reqCode, name: reqName });
    setCoverageModalOpen(true);
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P1': return 'error';
      case 'P2': return 'warning';
      case 'P3': return 'info';
      default: return 'default';
    }
  };

  const getStatusIcon = (passRate: number) => {
    if (passRate >= 0.8) return <CheckIcon color="success" fontSize="small" />;
    if (passRate >= 0.5) return <WarningIcon color="warning" fontSize="small" />;
    return <ErrorIcon color="error" fontSize="small" />;
  };

  // Filter coverage by selected UI
  const filteredCoverage = selectedUI === 'all' 
    ? Object.entries(coverageByUI).flatMap(([ui, reqs]) => 
        reqs.map(req => ({ ...req, ui }))
      )
    : coverageByUI[selectedUI]?.map(req => ({ ...req, ui: selectedUI })) || [];

  // Group by category
  const byCategory: { [cat: string]: typeof filteredCoverage } = {};
  filteredCoverage.forEach(req => {
    if (!byCategory[req.category]) {
      byCategory[req.category] = [];
    }
    byCategory[req.category].push(req);
  });

  // Calculate stats
  const totalRequirements = filteredCoverage.length;
  const totalTestcases = filteredCoverage.reduce((sum, req) => sum + req.testcase_count, 0);
  const avgPassRate = filteredCoverage.length > 0
    ? filteredCoverage.reduce((sum, req) => sum + req.pass_rate, 0) / filteredCoverage.length
    : 0;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Card>
          <CardContent sx={{ py: 1.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={2}>
                <StatsIcon color="primary" fontSize="large" />
                <Box>
                  <Typography variant="h5">Test Coverage Dashboard</Typography>
                  <Typography variant="caption" color="textSecondary">
                    Requirements-Testcases mapping by User Interface
                  </Typography>
                </Box>
              </Box>
              <Tooltip title="Refresh">
                <IconButton onClick={() => { refreshRequirements(); groupRequirementsByUI(); }}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Stats & Filter */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 250 }}>
          <InputLabel>User Interface</InputLabel>
          <Select
            value={selectedUI}
            onChange={(e) => setSelectedUI(e.target.value)}
            label="User Interface"
          >
            <MenuItem value="all">All User Interfaces</MenuItem>
            {availableUIs.map(ui => (
              <MenuItem key={ui} value={ui}>{ui}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box sx={{ display: 'flex', gap: 3, ml: 'auto' }}>
          <Box>
            <Typography variant="caption" color="textSecondary">Requirements</Typography>
            <Typography variant="h6">{totalRequirements}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="textSecondary">Testcases</Typography>
            <Typography variant="h6">{totalTestcases}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="textSecondary">Avg Pass Rate</Typography>
            <Typography 
              variant="h6" 
              color={avgPassRate >= 0.8 ? 'success.main' : avgPassRate >= 0.5 ? 'warning.main' : 'error.main'}
            >
              {Math.round(avgPassRate * 100)}%
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Loading */}
      {isLoading && (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      )}

      {/* Content */}
      {!isLoading && (
        <Box>
          {filteredCoverage.length === 0 ? (
            <Alert severity="info">
              {selectedUI === 'all'
                ? 'No coverage data available. Link testcases to requirements to see coverage.'
                : `No coverage data for ${selectedUI}. Try selecting a different user interface.`}
            </Alert>
          ) : (
            Object.entries(byCategory).map(([category, reqs]) => (
              <Accordion
                key={category}
                expanded={expandedCategories.has(category)}
                onChange={() => toggleCategory(category)}
                sx={{ mb: 1 }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={2} width="100%">
                    <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                      {category}
                    </Typography>
                    <Chip 
                      label={`${reqs.length} requirement${reqs.length !== 1 ? 's' : ''}`} 
                      size="small" 
                    />
                    <Chip 
                      label={`${reqs.reduce((sum, r) => sum + r.testcase_count, 0)} tests`} 
                      size="small" 
                      color="primary"
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {reqs.map((req) => (
                      <Card key={req.requirement_id} variant="outlined">
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                          <Box display="flex" alignItems="center" gap={2}>
                            {getStatusIcon(req.pass_rate)}
                            <Box flex={1}>
                              <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                                <Typography variant="body2" fontWeight="bold">
                                  {req.requirement_code}
                                </Typography>
                                <Typography variant="body2">
                                  {req.requirement_name}
                                </Typography>
                              </Box>
                              <Box display="flex" gap={1} alignItems="center">
                                <Chip
                                  label={req.priority}
                                  size="small"
                                  color={getPriorityColor(req.priority) as any}
                                />
                                <Typography variant="caption" color="textSecondary">
                                  {req.testcase_count} test{req.testcase_count !== 1 ? 's' : ''}
                                </Typography>
                                <Typography variant="caption" color="textSecondary">
                                  •
                                </Typography>
                                <Typography 
                                  variant="caption" 
                                  sx={{ 
                                    color: req.pass_rate >= 0.8 ? 'success.main' : 
                                           req.pass_rate >= 0.5 ? 'warning.main' : 'error.main'
                                  }}
                                >
                                  {Math.round(req.pass_rate * 100)}% pass rate
                                </Typography>
                                {selectedUI === 'all' && (
                                  <>
                                    <Typography variant="caption" color="textSecondary">
                                      •
                                    </Typography>
                                    <Chip label={req.ui} size="small" variant="outlined" />
                                  </>
                                )}
                              </Box>
                            </Box>
                            <Tooltip title="View coverage details">
                              <IconButton 
                                size="small" 
                                onClick={() => handleOpenRequirement(
                                  req.requirement_id, 
                                  req.requirement_code, 
                                  req.requirement_name
                                )}
                              >
                                <OpenInNewIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))
          )}
        </Box>
      )}

      {/* Coverage Modal */}
      {selectedRequirement && (
        <RequirementCoverageModal
          open={coverageModalOpen}
          onClose={() => setCoverageModalOpen(false)}
          requirementId={selectedRequirement.id}
          requirementCode={selectedRequirement.code}
          requirementName={selectedRequirement.name}
          getCoverage={getRequirementCoverage}
          onUnlinkTestcase={unlinkTestcase}
          onOpenLinkDialog={() => {
            setCoverageModalOpen(false);
            // Could open link dialog here if needed
          }}
        />
      )}
    </Box>
  );
};

export default Coverage;
