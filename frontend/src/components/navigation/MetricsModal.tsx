/**
 * Metrics Modal Component
 * Detailed view of low confidence nodes and edges with metrics breakdown
 */

import React, { useState, useMemo } from 'react';
import {
  DialogTitle,
  DialogContent,
  Typography,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  Close,
  TrendingDown,
  Speed,
  CheckCircle,
  Error,
  Warning,
  Refresh,
} from '@mui/icons-material';

import { LowConfidenceItems, LowConfidenceItem } from '../../types/navigation/Metrics_Types';
import { StyledDialog } from '../common/StyledDialog';
import { 
  formatExecutionTime, 
  formatSuccessRate, 
  getConfidenceColor 
} from '../../utils/metricsCalculations';

export interface MetricsModalProps {
  open: boolean;
  onClose: () => void;
  lowConfidenceItems: LowConfidenceItems;
  globalConfidence: number;
  onRefreshMetrics?: () => void;
  isLoading?: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`metrics-tabpanel-${index}`}
      aria-labelledby={`metrics-tab-${index}`}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
};

const MetricsTable: React.FC<{ items: LowConfidenceItem[] }> = ({ items }) => {
  if (items.length === 0) {
    return (
      <Alert severity="success" sx={{ mt: 1 }}>
        <Typography variant="body2">
          All items have confidence above 90% - Great job! 🎉
        </Typography>
      </Alert>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ mt: 1, maxHeight: 350 }}>
      <Table stickyHeader size="small" sx={{ '& .MuiTableRow-root': { height: '40px' } }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ py: 1 }}><strong>Name</strong></TableCell>
            <TableCell align="center" sx={{ py: 1 }}><strong>Confidence</strong></TableCell>
            <TableCell align="center" sx={{ py: 1 }}><strong>Volume</strong></TableCell>
            <TableCell align="center" sx={{ py: 1 }}><strong>Success Rate</strong></TableCell>
            <TableCell align="center" sx={{ py: 1 }}><strong>Avg Time</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow 
              key={item.id}
              sx={{ 
                '&:hover': { 
                  backgroundColor: 'rgba(0, 0, 0, 0.04) !important' 
                },
                backgroundColor: item.confidence < 0.5 ? 'rgba(244, 67, 54, 0.05)' : 'inherit'
              }}
            >
              <TableCell sx={{ py: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                    {item.label}
                  </Typography>
                  {item.confidence < 0.5 && (
                    <Tooltip title="Critical: Very low confidence">
                      <Error color="error" fontSize="small" />
                    </Tooltip>
                  )}
                </Box>
              </TableCell>
              <TableCell align="center" sx={{ py: 0.5 }}>
                <Chip
                  size="small"
                  label={item.confidence_percentage}
                  sx={{
                    backgroundColor: getConfidenceColor(item.confidence),
                    color: 'white',
                    fontWeight: 'bold',
                    minWidth: '60px',
                  }}
                />
              </TableCell>
              <TableCell align="center" sx={{ py: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                  <TrendingDown fontSize="small" color="action" />
                  <Typography variant="body2">{item.volume}</Typography>
                </Box>
              </TableCell>
              <TableCell align="center" sx={{ py: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                  <CheckCircle 
                    fontSize="small" 
                    color={item.success_rate > 0.8 ? "success" : item.success_rate > 0.5 ? "warning" : "error"} 
                  />
                  <Typography variant="body2">{formatSuccessRate(item.success_rate)}</Typography>
                </Box>
              </TableCell>
              <TableCell align="center" sx={{ py: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                  <Speed fontSize="small" color="action" />
                  <Typography variant="body2">{formatExecutionTime(item.avg_execution_time)}</Typography>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export const MetricsModal: React.FC<MetricsModalProps> = ({
  open,
  onClose,
  lowConfidenceItems,
  globalConfidence,
  onRefreshMetrics,
  isLoading = false,
}) => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const globalConfidencePercentage = (globalConfidence * 100).toFixed(1);
  const globalConfidenceColor = getConfidenceColor(globalConfidence);

  const summaryStats = useMemo(() => {
    const totalItems = lowConfidenceItems.total_count;
    const criticalItems = [...lowConfidenceItems.nodes, ...lowConfidenceItems.edges]
      .filter(item => item.confidence < 0.5).length;
    
    return {
      totalItems,
      criticalItems,
      nodeCount: lowConfidenceItems.nodes.length,
      edgeCount: lowConfidenceItems.edges.length,
    };
  }, [lowConfidenceItems]);

  return (
    <StyledDialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { maxHeight: '80vh' }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6" component="div">
            Navigation Confidence Metrics
          </Typography>
          
          {/* Global confidence indicator */}
          <Chip
            label={`Global: ${globalConfidencePercentage}%`}
            sx={{
              backgroundColor: globalConfidenceColor,
              color: 'white',
              fontWeight: 'bold',
            }}
          />
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {onRefreshMetrics && (
            <Tooltip title="Refresh metrics">
              <IconButton onClick={onRefreshMetrics} disabled={isLoading}>
                <Refresh />
              </IconButton>
            </Tooltip>
          )}
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      {isLoading && <LinearProgress />}

      <DialogContent sx={{ pb: 2 }}>
        {/* Summary stats */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Chip
            icon={<Warning />}
            label={`${summaryStats.totalItems} items below 90%`}
            color={summaryStats.totalItems > 0 ? 'warning' : 'success'}
            variant="outlined"
          />
          
          {summaryStats.criticalItems > 0 && (
            <Chip
              icon={<Error />}
              label={`${summaryStats.criticalItems} critical (< 50%)`}
              color="error"
              variant="outlined"
            />
          )}
          
          <Chip
            label={`${summaryStats.nodeCount} nodes`}
            variant="outlined"
            color="primary"
          />
          
          <Chip
            label={`${summaryStats.edgeCount} edges`}
            variant="outlined"
            color="secondary"
          />
        </Box>


        {/* Tabs for nodes and edges */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="metrics tabs">
            <Tab 
              label={`Nodes (${lowConfidenceItems.nodes.length})`} 
              id="metrics-tab-0"
              aria-controls="metrics-tabpanel-0"
            />
            <Tab 
              label={`Edges (${lowConfidenceItems.edges.length})`} 
              id="metrics-tab-1"
              aria-controls="metrics-tabpanel-1"
            />
          </Tabs>
        </Box>

        {/* Tab panels */}
        <TabPanel value={tabValue} index={0}>
          <MetricsTable items={lowConfidenceItems.nodes} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <MetricsTable items={lowConfidenceItems.edges} />
        </TabPanel>
      </DialogContent>

    </StyledDialog>
  );
};
