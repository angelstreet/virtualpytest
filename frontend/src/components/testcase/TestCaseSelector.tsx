import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, TextField, Autocomplete, Chip, Typography, CircularProgress, Paper,
  List, ListItem, ListItemButton, InputAdornment, IconButton,
} from '@mui/material';
import {
  Search as SearchIcon,
  Folder as FolderIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface TestCaseItem {
  testcase_id: string;
  testcase_name: string;
  description?: string;
  userinterface_name?: string;
  environment?: 'dev' | 'test' | 'prod';
  current_version?: number;
  execution_count?: number;
  last_execution_success?: boolean;
  folder?: string;
  tags?: string[];
  graph_json?: {
    nodes?: any[];
  };
  created_at?: string;
  updated_at?: string;
}

export interface TestCaseSelectorProps {
  onLoad: (testcaseId: string) => void;
  onDelete?: (testcaseId: string, testcaseName: string) => void;
  selectedTestCaseId?: string | null;
}

export const TestCaseSelector: React.FC<TestCaseSelectorProps> = ({
  onLoad,
  onDelete,
  selectedTestCaseId,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allTestCases, setAllTestCases] = useState<TestCaseItem[]>([]);
  const [allFolderNames, setAllFolderNames] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<Array<{ name: string; color: string }>>([]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string>('All');

  // Ref to prevent duplicate API calls in React Strict Mode
  const isLoadingRef = React.useRef(false);

  // Load test cases on mount
  useEffect(() => {
    // Prevent duplicate calls in React Strict Mode
    if (isLoadingRef.current) {
      console.log('[@TestCaseSelector] Load already in progress, skipping duplicate call');
      return;
    }
    
    console.log('[@TestCaseSelector] Loading test cases...');
    loadTestCases();
  }, []);

  const loadTestCases = async () => {
    // Prevent concurrent calls
    if (isLoadingRef.current) {
      return;
    }
    
    isLoadingRef.current = true;
    
    try {
      setLoading(true);
      setError(null);

      // Note: buildServerUrl automatically adds team_id parameter
      // Load test cases
      const testCasesResponse = await fetch(
        buildServerUrl('/server/testcase/list')
      );
      const testCasesData = await testCasesResponse.json();

      // Load folders and tags
      const foldersTagsResponse = await fetch(
        buildServerUrl('/server/testcase/folders-tags')
      );
      const foldersTagsData = await foldersTagsResponse.json();

      if (testCasesData.success) {
        setAllTestCases(testCasesData.testcases || []);
        console.log('[@TestCaseSelector] ✅ Loaded', testCasesData.testcases?.length || 0, 'test cases');
      } else {
        throw new Error(testCasesData.error || 'Failed to load test cases');
      }

      if (foldersTagsData.success) {
        setAllFolderNames(foldersTagsData.folders?.map((f: any) => f.name) || []);
        setAllTags(foldersTagsData.tags || []);
      }
    } catch (err) {
      console.error('[@TestCaseSelector] ❌ Error loading test cases:', err);
      setError(err instanceof Error ? err.message : 'Failed to load test cases');
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  };

  // Filter test cases
  const filteredTestCases = useMemo(() => {
    let items = [...allTestCases];

    // Apply folder filter
    if (selectedFolder && selectedFolder !== 'All') {
      items = items.filter(item => item.folder === selectedFolder);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      items = items.filter(item =>
        item.testcase_name.toLowerCase().includes(query) ||
        item.description?.toLowerCase().includes(query) ||
        item.userinterface_name?.toLowerCase().includes(query)
      );
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      items = items.filter(item =>
        item.tags && item.tags.some(tag => selectedTags.includes(tag))
      );
    }

    return items;
  }, [allTestCases, searchQuery, selectedTags, selectedFolder]);

  // Get environment color for chips
  const getEnvironmentColor = (env?: string) => {
    switch (env) {
      case 'prod': return 'error';
      case 'test': return 'warning';
      case 'dev': return 'success';
      default: return 'default';
    }
  };

  // Handle item selection
  const handleItemSelect = (testcaseId: string) => {
    console.log('[@TestCaseSelector] 🎯 Test case selected:', testcaseId);
    onLoad(testcaseId);
  };

  // Handle delete click
  const handleDeleteClick = (e: React.MouseEvent, testcaseId: string, testcaseName: string) => {
    e.stopPropagation();
    if (onDelete) {
      onDelete(testcaseId, testcaseName);
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
      {/* Filters Section - All in one row, equal sizes */}
      <Box sx={{ display: 'flex', gap: 1, mb: 1, mt: 1, alignItems: 'flex-start' }}>
        <TextField
          size="small"
          placeholder="Search by name, description, UI..."
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
          value={selectedFolder}
          onChange={(_event, newValue) => setSelectedFolder(newValue || 'All')}
          options={['All', ...allFolderNames]}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Folder"
              InputProps={{
                ...params.InputProps,
                startAdornment: (
                  <>
                    <InputAdornment position="start">
                      <FolderIcon fontSize="small" />
                    </InputAdornment>
                    {params.InputProps.startAdornment}
                  </>
                ),
              }}
              InputLabelProps={{
                ...params.InputLabelProps,
                shrink: true,
                sx: { backgroundColor: 'background.paper', px: 0.5 }
              }}
            />
          )}
          sx={{ flex: 1 }}
        />

        <Autocomplete
          size="small"
          multiple
          value={selectedTags}
          onChange={(_event, newValue) => setSelectedTags(newValue)}
          options={allTags.map(t => t.name)}
          disabled={allTags.length === 0}
          renderTags={(value, getTagProps) =>
            value.map((option, index) => {
              const tag = allTags.find(t => t.name === option);
              return (
                <Chip
                  label={option}
                  size="small"
                  {...getTagProps({ index })}
                  sx={{
                    height: '20px',
                    backgroundColor: tag?.color || '#9e9e9e',
                    color: 'white',
                    '& .MuiChip-deleteIcon': {
                      color: 'rgba(255,255,255,0.7)',
                      '&:hover': { color: 'white' }
                    }
                  }}
                />
              );
            })
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label="Tags"
              placeholder={allTags.length === 0 ? 'No tags' : 'Filter...'}
              InputLabelProps={{
                ...params.InputLabelProps,
                shrink: true,
                sx: { backgroundColor: 'background.paper', px: 0.5 }
              }}
            />
          )}
          sx={{ flex: 1 }}
        />
      </Box>

      {/* Test Case List - Compact 2-line format */}
      <Box>
        <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto' }}>
          {filteredTestCases.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {allTestCases.length === 0 
                  ? 'No test cases found. Create one first!'
                  : 'No test cases match your filters'
                }
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {filteredTestCases.map(tc => {
                const isSelected = selectedTestCaseId === tc.testcase_id;
                const blockCount = tc.graph_json?.nodes?.length || 0;
                
                return (
                  <ListItem
                    key={tc.testcase_id}
                    disablePadding
                    sx={{
                      borderBottom: 1,
                      borderColor: 'divider',
                      '&:last-child': { borderBottom: 0 },
                      bgcolor: isSelected ? 'primary.main' : 'transparent',
                      '&:hover': { bgcolor: isSelected ? 'primary.dark' : 'action.hover' },
                    }}
                  >
                    <ListItemButton
                      onClick={() => handleItemSelect(tc.testcase_id)}
                      selected={isSelected}
                      sx={{
                        py: 0.5,
                        px: 1.5,
                        display: 'flex',
                        flexDirection: 'row',  // Single line layout
                        alignItems: 'center',
                        gap: 1,
                        color: isSelected ? 'primary.contrastText' : 'inherit'
                      }}
                    >
                      {/* Single line: Badge + Name + Description + UI + Blocks + Env + Version + Status + Tags + Delete */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                        {/* Badge */}
                        <Chip
                          label="TC"
                          size="small"
                          color="secondary"
                          sx={{
                            height: '18px',
                            fontSize: '0.65rem',
                            minWidth: '28px',
                            fontWeight: 'bold',
                            flexShrink: 0,
                            bgcolor: isSelected ? 'rgba(255,255,255,0.9)' : undefined,
                            color: isSelected ? 'secondary.main' : undefined
                          }}
                        />
                        
                        {/* Name */}
                        <Typography
                          variant="body2"
                          sx={{
                            fontSize: '0.875rem',
                            fontWeight: 'bold',
                            minWidth: 120,
                            maxWidth: 180,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                          }}
                        >
                          {tc.testcase_name}
                        </Typography>
                        
                        {/* Separator */}
                        <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                        
                        {/* Description */}
                        <Typography
                          variant="caption"
                          sx={{
                            fontSize: '0.75rem',
                            flex: '1 1 200px',
                            minWidth: 0,
                            opacity: 0.85,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {tc.description || 'No description'}
                        </Typography>
                        
                        {/* Separator */}
                        <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                        
                        {/* UI + Blocks */}
                        <Typography
                          variant="caption"
                          sx={{
                            fontSize: '0.75rem',
                            opacity: 0.8,
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                            minWidth: 120,
                          }}
                        >
                          {tc.userinterface_name || 'No UI'} • {blockCount} blocks
                        </Typography>
                        
                        {/* Separator */}
                        <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                        {/* Environment Badge */}
                        <Chip
                          label={(tc.environment || 'dev').toUpperCase()}
                          size="small"
                          color={getEnvironmentColor(tc.environment)}
                          sx={{
                            height: '16px',
                            fontSize: '0.6rem',
                            fontWeight: 'bold',
                            flexShrink: 0,
                            bgcolor: isSelected ? 'rgba(255,255,255,0.9)' : undefined,
                            color: isSelected 
                              ? tc.environment === 'prod' ? 'error.main' 
                                : tc.environment === 'test' ? 'warning.main' 
                                : 'success.main'
                              : undefined
                          }}
                        />
                        
                        {/* Version */}
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', opacity: 0.8, flexShrink: 0 }}>
                          v{tc.current_version || 1}
                        </Typography>
                        
                        {/* Separator */}
                        <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                        
                        {/* Execution Status */}
                        <Typography
                          variant="caption"
                          sx={{
                            fontSize: '0.7rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.25,
                            opacity: 0.85,
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                            minWidth: 100,
                          }}
                        >
                          {tc.execution_count && tc.execution_count > 0 ? (
                            <>
                              {tc.last_execution_success ? (
                                <CheckCircleIcon 
                                  fontSize="inherit" 
                                  sx={{ 
                                    fontSize: '0.9rem',
                                    color: isSelected ? 'rgba(255,255,255,0.9)' : 'success.main'
                                  }} 
                                />
                              ) : (
                                <ErrorIcon 
                                  fontSize="inherit" 
                                  sx={{ 
                                    fontSize: '0.9rem',
                                    color: isSelected ? 'rgba(255,255,255,0.9)' : 'error.main'
                                  }} 
                                />
                              )}
                              {tc.execution_count} run{tc.execution_count > 1 ? 's' : ''}
                            </>
                          ) : (
                            'Never executed'
                          )}
                        </Typography>
                        
                        {/* Tags */}
                        {tc.tags && tc.tags.length > 0 && (
                          <>
                            <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                            <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                              {tc.tags.slice(0, 2).map(tagName => {
                                const tag = allTags.find(t => t.name === tagName);
                                return (
                                  <Chip
                                    key={tagName}
                                    label={tagName}
                                    size="small"
                                    sx={{
                                      height: '14px',
                                      fontSize: '0.6rem',
                                      backgroundColor: isSelected ? 'rgba(255,255,255,0.9)' : (tag?.color || '#9e9e9e'),
                                      color: isSelected ? 'primary.main' : 'white'
                                    }}
                                  />
                                );
                              })}
                              {tc.tags.length > 2 && (
                                <Typography variant="caption" sx={{ fontSize: '0.65rem', opacity: 0.7 }}>
                                  +{tc.tags.length - 2}
                                </Typography>
                              )}
                            </Box>
                          </>
                        )}
                        
                        {/* Delete Button */}
                        {onDelete && (
                          <IconButton
                            size="small"
                            onClick={(e) => handleDeleteClick(e, tc.testcase_id, tc.testcase_name)}
                            sx={{
                              p: 0.5,
                              ml: 'auto',
                              flexShrink: 0,
                              color: isSelected ? 'primary.contrastText' : 'error.main',
                              '&:hover': {
                                bgcolor: isSelected ? 'rgba(255,255,255,0.2)' : 'error.light'
                              }
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        )}
                      </Box>
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          )}
        </Paper>
      </Box>

      {/* Summary Footer */}
      <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          {filteredTestCases.length} test case{filteredTestCases.length !== 1 ? 's' : ''}
          {selectedFolder && selectedFolder !== 'All' && ` in ${selectedFolder}`}
          {selectedTags.length > 0 && ` • ${selectedTags.join(', ')}`}
          {searchQuery && ` • "${searchQuery}"`}
        </Typography>
        {(searchQuery || selectedTags.length > 0 || (selectedFolder && selectedFolder !== 'All')) && (
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer', textDecoration: 'underline', fontSize: '0.75rem' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedTags([]);
              setSelectedFolder('All');
            }}
          >
            Clear filters
          </Typography>
        )}
      </Box>
    </Box>
  );
};

