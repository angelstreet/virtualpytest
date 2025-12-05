import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, TextField, Autocomplete, Chip, Typography, CircularProgress, Paper,
  List, ListItem, InputAdornment, IconButton, Checkbox, Collapse,
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  Link as LinkIcon,
  PlayArrow as ScriptIcon,
  Campaign as CampaignIcon,
} from '@mui/icons-material';
import { useCampaignResults, CampaignResult } from '../../hooks/pages/useCampaignResults';
import { formatToLocalTime } from '../../utils/dateUtils';
import { getR2Url, extractR2Path, isCloudflareR2Url } from '../../utils/infrastructure/cloudflareUtils';

export interface CampaignResultsListProps {
  onDiscardToggle?: (resultId: string, discardValue: boolean) => Promise<void>;
}

export const CampaignResultsList: React.FC<CampaignResultsListProps> = ({
  onDiscardToggle,
}) => {
  const { getAllCampaignResults } = useCampaignResults();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allResults, setAllResults] = useState<CampaignResult[]>([]);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('All');
  const [selectedUserinterface, setSelectedUserinterface] = useState<string>('All');

  // Ref to prevent duplicate API calls in React Strict Mode
  const isLoadingRef = React.useRef(false);

  // Load campaign results on mount
  useEffect(() => {
    if (isLoadingRef.current) {
      console.log('[@CampaignResultsList] Load already in progress, skipping duplicate call');
      return;
    }
    
    console.log('[@CampaignResultsList] Loading campaign results...');
    loadResults();
  }, []);

  const loadResults = async () => {
    if (isLoadingRef.current) {
      return;
    }
    
    isLoadingRef.current = true;
    
    try {
      setLoading(true);
      setError(null);
      
      const results = await getAllCampaignResults();
      setAllResults(results);
      console.log('[@CampaignResultsList] ✅ Loaded', results.length, 'campaign results');
    } catch (err) {
      console.error('[@CampaignResultsList] ❌ Error loading campaign results:', err);
      setError(err instanceof Error ? err.message : 'Failed to load campaign results');
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  };

  // Get unique userinterfaces for filter
  const allUserinterfaces = useMemo(() => {
    const interfaces = new Set(allResults.map(r => r.userinterface_name).filter(Boolean));
    return Array.from(interfaces);
  }, [allResults]);

  // Filter results
  const filteredResults = useMemo(() => {
    let items = [...allResults];

    // Apply status filter
    if (selectedStatus && selectedStatus !== 'All') {
      if (selectedStatus === 'Pass') {
        items = items.filter(item => item.success);
      } else if (selectedStatus === 'Fail') {
        items = items.filter(item => !item.success);
      }
    }

    // Apply userinterface filter
    if (selectedUserinterface && selectedUserinterface !== 'All') {
      items = items.filter(item => item.userinterface_name === selectedUserinterface);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      items = items.filter(item =>
        item.campaign_name.toLowerCase().includes(query) ||
        item.host_name.toLowerCase().includes(query) ||
        item.device_name.toLowerCase().includes(query)
      );
    }

    return items;
  }, [allResults, searchQuery, selectedStatus, selectedUserinterface]);

  // Format duration helper
  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(1);
    return `${minutes}m ${seconds}s`;
  };

  // Open R2 URL with automatic signed URL generation (handles both public and private modes)
  const handleOpenR2Url = async (url: string) => {
    try {
      // Extract path from full URL if needed (database stores full public URLs)
      let path = url;
      if (isCloudflareR2Url(url)) {
        const extracted = extractR2Path(url);
        if (extracted) {
          path = extracted;
        }
      }
      
      // getR2Url handles both public and private modes automatically
      const signedUrl = await getR2Url(path);
      window.open(signedUrl, '_blank');
    } catch (error) {
      console.error('[@CampaignResultsList] Failed to open R2 URL:', error);
      setError('Failed to open file. Please try again.');
    }
  };

  // Handle row expansion
  const handleRowExpand = (campaignId: string) => {
    const newExpandedRows = new Set(expandedRows);
    
    if (expandedRows.has(campaignId)) {
      newExpandedRows.delete(campaignId);
    } else {
      newExpandedRows.add(campaignId);
    }
    
    setExpandedRows(newExpandedRows);
  };

  // Handle discard toggle
  const handleDiscardToggle = async (resultId: string, discardValue: boolean) => {
    if (onDiscardToggle) {
      try {
        await onDiscardToggle(resultId, discardValue);
        // Update local state
        setAllResults(prev => prev.map(r => 
          r.id === resultId ? { ...r, discard: discardValue } : r
        ));
      } catch (error) {
        console.error('[@CampaignResultsList] Error toggling discard:', error);
      }
    } else {
      // Update local state only
      setAllResults(prev => prev.map(r => 
        r.id === resultId ? { ...r, discard: discardValue } : r
      ));
    }
  };

  // Render loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  // Render error state
  if (error) {
    return (
      <Box sx={{ p: 2, bgcolor: 'error.light', borderRadius: 1 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Filters Section */}
      <Box sx={{ display: 'flex', gap: 1, mb: 1, mt: 1, alignItems: 'flex-start' }}>
        <TextField
          size="small"
          placeholder="Search by campaign, host, device..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ flex: 1 }}
        />

        <Autocomplete
          size="small"
          value={selectedStatus}
          onChange={(_event, newValue) => setSelectedStatus(newValue || 'All')}
          options={['All', 'Pass', 'Fail']}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Status"
              InputLabelProps={{
                shrink: true,
                sx: { backgroundColor: 'background.paper', px: 0.5 }
              }}
            />
          )}
          sx={{ minWidth: 120 }}
        />

        <Autocomplete
          size="small"
          value={selectedUserinterface}
          onChange={(_event, newValue) => setSelectedUserinterface(newValue || 'All')}
          options={['All', ...allUserinterfaces]}
          renderInput={(params) => (
            <TextField
              {...params}
              label="UI"
              InputLabelProps={{
                shrink: true,
                sx: { backgroundColor: 'background.paper', px: 0.5 }
              }}
            />
          )}
          sx={{ minWidth: 150 }}
        />
      </Box>

      {/* Results List */}
      <Box>
        <Paper variant="outlined" sx={{ maxHeight: 600, overflow: 'auto' }}>
          {filteredResults.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {allResults.length === 0 
                  ? 'No campaign results found'
                  : 'No campaign results match your filters'
                }
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {filteredResults.map(result => (
                <React.Fragment key={result.id}>
                  {/* Main Result Row */}
                  <ListItem
                    disablePadding
                    sx={{
                      borderBottom: 1,
                      borderColor: 'divider',
                      opacity: result.discard ? 0.5 : 1,
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', py: 0.5, px: 1.5, gap: 1 }}>
                      {/* Expand Button */}
                      <IconButton
                        size="small"
                        onClick={() => handleRowExpand(result.id)}
                        sx={{ flexShrink: 0 }}
                      >
                        {expandedRows.has(result.id) ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                      </IconButton>

                      {/* Badge */}
                      <Chip
                        icon={<CampaignIcon />}
                        label="C"
                        size="small"
                        color="primary"
                        sx={{ height: '18px', fontSize: '0.65rem', minWidth: '28px', flexShrink: 0 }}
                      />

                      {/* Campaign Name */}
                      <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: 120, flexShrink: 0 }}>
                        {result.campaign_name}
                      </Typography>

                      <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                      {/* UI Name */}
                      <Typography variant="caption" sx={{ minWidth: 100, flexShrink: 0, opacity: 0.85 }}>
                        {result.userinterface_name || 'N/A'}
                      </Typography>

                      <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                      {/* Host:Device */}
                      <Typography variant="caption" sx={{ minWidth: 120, flexShrink: 0, opacity: 0.85 }}>
                        {result.host_name}:{result.device_name}
                      </Typography>

                      <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                      {/* Status */}
                      <Chip
                        icon={result.success ? <PassIcon /> : <FailIcon />}
                        label={result.success ? 'PASS' : 'FAIL'}
                        color={result.success ? 'success' : 'error'}
                        size="small"
                        sx={{ height: '18px', fontSize: '0.65rem', flexShrink: 0 }}
                      />

                      <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                      {/* Duration */}
                      <Typography variant="caption" sx={{ minWidth: 60, flexShrink: 0, opacity: 0.8 }}>
                        {result.execution_time_ms ? formatDuration(result.execution_time_ms) : 'N/A'}
                      </Typography>

                      <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                      {/* Started Time */}
                      <Typography variant="caption" sx={{ minWidth: 140, flexShrink: 0, opacity: 0.8 }}>
                        {formatToLocalTime(result.started_at)}
                      </Typography>

                      {/* Report Link */}
                      {result.html_report_r2_url && (
                        <IconButton
                          size="small"
                          onClick={() => handleOpenR2Url(result.html_report_r2_url!)}
                          sx={{ flexShrink: 0, color: 'primary.main' }}
                        >
                          <LinkIcon fontSize="small" />
                        </IconButton>
                      )}

                      {/* Discard Checkbox */}
                      <Checkbox
                        size="small"
                        checked={result.discard || false}
                        onChange={(e) => handleDiscardToggle(result.id, e.target.checked)}
                        sx={{ ml: 'auto', flexShrink: 0 }}
                      />
                    </Box>
                  </ListItem>

                  {/* Expandable Script Results */}
                  {expandedRows.has(result.id) && (
                    <Collapse in={true} timeout="auto">
                      <Box sx={{ bgcolor: 'rgba(0, 0, 0, 0.02)', borderBottom: 1, borderColor: 'divider' }}>
                        {result.script_results && result.script_results.length > 0 ? (
                          result.script_results.map((script) => (
                            <Box
                              key={script.id}
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                py: 0.5,
                                px: 1.5,
                                pl: 6,
                                gap: 1,
                                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                              }}
                            >
                              <ScriptIcon fontSize="small" sx={{ flexShrink: 0 }} />

                              <Typography variant="body2" sx={{ minWidth: 120, flexShrink: 0 }}>
                                {script.script_name}
                              </Typography>

                              {/* Tags */}
                              {script.tags && script.tags.length > 0 && (
                                <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                                  {script.tags.map(tag => (
                                    <Chip
                                      key={tag.name}
                                      label={tag.name}
                                      size="small"
                                      sx={{
                                        height: '14px',
                                        fontSize: '0.6rem',
                                        backgroundColor: tag.color,
                                        color: 'white'
                                      }}
                                    />
                                  ))}
                                </Box>
                              )}

                              <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                              <Chip
                                icon={script.success ? <PassIcon /> : <FailIcon />}
                                label={script.success ? 'PASS' : 'FAIL'}
                                color={script.success ? 'success' : 'error'}
                                size="small"
                                sx={{ height: '16px', fontSize: '0.6rem', flexShrink: 0 }}
                              />

                              <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                              <Typography variant="caption" sx={{ minWidth: 60, flexShrink: 0, opacity: 0.8 }}>
                                {script.execution_time_ms ? formatDuration(script.execution_time_ms) : 'N/A'}
                              </Typography>

                              {script.html_report_r2_url && (
                                <IconButton
                                  size="small"
                                  onClick={() => handleOpenR2Url(script.html_report_r2_url!)}
                                  sx={{ ml: 'auto', flexShrink: 0, color: 'primary.main' }}
                                >
                                  <LinkIcon fontSize="small" />
                                </IconButton>
                              )}
                            </Box>
                          ))
                        ) : (
                          <Box sx={{ py: 1, px: 1.5, pl: 6 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                              No script results linked to this campaign
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    </Collapse>
                  )}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      </Box>

      {/* Summary Footer */}
      <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          {filteredResults.length} campaign result{filteredResults.length !== 1 ? 's' : ''}
          {selectedStatus && selectedStatus !== 'All' && ` • ${selectedStatus}`}
          {selectedUserinterface && selectedUserinterface !== 'All' && ` • ${selectedUserinterface}`}
          {searchQuery && ` • "${searchQuery}"`}
        </Typography>
        {(searchQuery || selectedStatus !== 'All' || selectedUserinterface !== 'All') && (
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer', textDecoration: 'underline', fontSize: '0.75rem' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedStatus('All');
              setSelectedUserinterface('All');
            }}
          >
            Clear filters
          </Typography>
        )}
      </Box>
    </Box>
  );
};


