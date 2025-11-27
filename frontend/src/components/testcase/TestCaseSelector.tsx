import React, { useState, useEffect, useMemo, forwardRef, useImperativeHandle } from 'react';
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
  PlayArrow as ScriptIcon,
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { getCachedTestCaseList, invalidateTestCaseListCache } from '../../utils/testcaseCache';

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
  type: 'testcase'; // NEW: Type discriminator
}

// NEW: Script item interface
export interface ScriptItem {
  script_name: string;
  folder?: string;
  tags?: string[];
  type: 'script'; // NEW: Type discriminator
}

// Unified item type
export type ExecutableItem = TestCaseItem | ScriptItem;

export interface TestCaseSelectorProps {
  onLoad: (testcaseId: string) => void;
  onDelete?: (testcaseId: string, testcaseName: string) => Promise<void>;
  selectedTestCaseId?: string | null;
  testCasesOnly?: boolean; // If true, only show test cases (no scripts)
}

export const TestCaseSelector = forwardRef<{ refresh: () => void }, TestCaseSelectorProps>(({
  onLoad,
  onDelete,
  selectedTestCaseId,
  testCasesOnly = false,
}, ref) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allItems, setAllItems] = useState<ExecutableItem[]>([]); // Changed to unified list
  const [allFolderNames, setAllFolderNames] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<Array<{ name: string; color: string }>>([]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string>('All');
  const [selectedType, setSelectedType] = useState<string>('All');

  // Ref to prevent duplicate API calls in React Strict Mode
  const isLoadingRef = React.useRef(false);

  // Expose refresh method to parent via ref
  useImperativeHandle(ref, () => ({
    refresh: loadAll,
  }));

  // Load test cases AND scripts on mount
  useEffect(() => {
    // Prevent duplicate calls in React Strict Mode
    if (isLoadingRef.current) {
      console.log('[@TestCaseSelector] Load already in progress, skipping duplicate call');
      return;
    }
    
    console.log('[@TestCaseSelector] Loading test cases and scripts...');
    loadAll();
  }, []);

  const loadAll = async () => {
    // Prevent concurrent calls
    if (isLoadingRef.current) {
      return;
    }
    
    isLoadingRef.current = true;
    
    try {
      setLoading(true);
      setError(null);

      // Load test cases (with shared cache)
      const testCasesData = await getCachedTestCaseList(
        buildServerUrl('/server/testcase/list')
      );

      // Load scripts
      const scriptsResponse = await fetch(
        buildServerUrl('/server/script/list')
      );
      const scriptsData = await scriptsResponse.json();

      // Load folders and tags
      const foldersTagsResponse = await fetch(
        buildServerUrl('/server/testcase/folders-tags')
      );
      const foldersTagsData = await foldersTagsResponse.json();

      const testCases: TestCaseItem[] = (testCasesData.testcases || []).map((tc: any) => ({
        ...tc,
        type: 'testcase' as const,
      }));

      const scripts: ScriptItem[] = (scriptsData.scripts || []).map((script: string) => ({
        script_name: script,
        type: 'script' as const,
        folder: '(Root)',
        tags: [],
      }));

      // Combine test cases and scripts (filter scripts if testCasesOnly is true)
      const combined: ExecutableItem[] = testCasesOnly ? testCases : [...testCases, ...scripts];

      if (testCasesData.success) {
        setAllItems(combined);
        console.log('[@TestCaseSelector] ✅ Loaded', testCases.length, 'test cases and', scripts.length, 'scripts');
      } else {
        throw new Error(testCasesData.error || 'Failed to load test cases');
      }

      if (foldersTagsData.success) {
        setAllFolderNames(foldersTagsData.folders?.map((f: any) => f.name) || []);
        setAllTags(foldersTagsData.tags || []);
      }
    } catch (err) {
      console.error('[@TestCaseSelector] ❌ Error loading:', err);
      setError(err instanceof Error ? err.message : 'Failed to load test cases and scripts');
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  };

  // Filter items (test cases + scripts)
  const filteredItems = useMemo(() => {
    let items = [...allItems];

    // Apply type filter
    if (selectedType && selectedType !== 'All') {
      items = items.filter(item => item.type === selectedType.toLowerCase());
    }

    // Apply folder filter
    if (selectedFolder && selectedFolder !== 'All') {
      items = items.filter(item => item.folder === selectedFolder);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      items = items.filter(item => {
        if (item.type === 'testcase') {
          return item.testcase_name.toLowerCase().includes(query) ||
                 item.description?.toLowerCase().includes(query) ||
                 item.userinterface_name?.toLowerCase().includes(query);
        } else {
          // Script
          return item.script_name.toLowerCase().includes(query);
        }
      });
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      items = items.filter(item =>
        item.tags && item.tags.some(tag => selectedTags.includes(tag))
      );
    }

    return items;
  }, [allItems, searchQuery, selectedTags, selectedFolder, selectedType]);

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
  const handleItemSelect = (item: ExecutableItem) => {
    if (item.type === 'testcase') {
      console.log('[@TestCaseSelector] 🎯 Test case selected:', item.testcase_id);
      onLoad(item.testcase_id);
    } else {
      // Script selected - scripts can't be loaded in test case builder
      console.log('[@TestCaseSelector] ℹ️ Script selected (not loadable):', item.script_name);
    }
  };

  // Handle delete click - just call parent handler, don't refresh
  const handleDeleteClick = (e: React.MouseEvent, item: ExecutableItem) => {
    e.stopPropagation();
    
    if (item.type === 'script') {
      console.log('[@TestCaseSelector] Scripts cannot be deleted from here');
      return;
    }
    
    if (onDelete) {
      // Call the parent delete handler (opens confirmation dialog)
      // Parent will call refresh() via ref after successful deletion
      onDelete(item.testcase_id, item.testcase_name);
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
          placeholder="Search by name..."
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

        {/* Type Filter - Only show if scripts are enabled */}
        {!testCasesOnly && (
          <Autocomplete
            size="small"
            value={selectedType}
            onChange={(_event, newValue) => setSelectedType(newValue || 'All')}
            options={['All', 'TestCase', 'Script']}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Type"
                InputLabelProps={{
                  shrink: true,
                  sx: { backgroundColor: 'background.paper', px: 0.5 }
                }}
              />
            )}
            sx={{ minWidth: 120 }}
          />
        )}

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

      {/* Item List - Compact format for test cases and scripts */}
      <Box>
        <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto' }}>
          {filteredItems.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {allItems.length === 0 
                  ? 'No test cases or scripts found. Create one first!'
                  : 'No items match your filters'
                }
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {filteredItems.map(item => {
                const isTestCase = item.type === 'testcase';
                const itemId = isTestCase ? item.testcase_id : item.script_name;
                const isSelected = selectedTestCaseId === itemId;
                
                // For test cases, get block count
                const blockCount = isTestCase ? (item.graph_json?.nodes?.length || 0) : undefined;
                
                return (
                  <ListItem
                    key={itemId}
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
                      onClick={() => handleItemSelect(item)}
                      selected={isSelected}
                      sx={{
                        py: 0.5,
                        px: 1.5,
                        display: 'flex',
                        flexDirection: 'row',
                        alignItems: 'center',
                        gap: 1,
                        color: isSelected ? 'primary.contrastText' : 'inherit'
                      }}
                    >
                      {/* Single line: Badge + Name + Description + UI + Blocks + Env + Version + Status + Tags + Delete */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                        {/* Badge */}
                        <Chip
                          icon={isTestCase ? undefined : <ScriptIcon />}
                          label={isTestCase ? "TC" : "S"}
                          size="small"
                          color={isTestCase ? "secondary" : "primary"}
                          sx={{
                            height: '18px',
                            fontSize: '0.65rem',
                            minWidth: '28px',
                            fontWeight: 'bold',
                            flexShrink: 0,
                            bgcolor: isSelected ? 'rgba(255,255,255,0.9)' : undefined,
                            color: isSelected ? (isTestCase ? 'secondary.main' : 'primary.main') : undefined
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
                          {isTestCase ? item.testcase_name : item.script_name}
                        </Typography>
                        
                        {/* Separator */}
                        <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                        
                        {/* Description (Test Cases only) */}
                        {isTestCase && (
                          <>
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
                              {item.description || 'No description'}
                            </Typography>
                            
                            {/* Separator */}
                            <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                          </>
                        )}
                        
                        {/* UI + Blocks (Test Cases only) */}
                        {isTestCase && (
                          <>
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
                              {item.userinterface_name || 'No UI'} • {blockCount} blocks
                            </Typography>
                            
                            {/* Separator */}
                            <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>

                            {/* Environment Badge */}
                            <Chip
                              label={(item.environment || 'dev').toUpperCase()}
                              size="small"
                              color={getEnvironmentColor(item.environment)}
                              sx={{
                                height: '16px',
                                fontSize: '0.6rem',
                                fontWeight: 'bold',
                                flexShrink: 0,
                                bgcolor: isSelected ? 'rgba(255,255,255,0.9)' : undefined,
                                color: isSelected 
                                  ? item.environment === 'prod' ? 'error.main' 
                                    : item.environment === 'test' ? 'warning.main' 
                                    : 'success.main'
                                  : undefined
                              }}
                            />
                            
                            {/* Version */}
                            <Typography variant="caption" sx={{ fontSize: '0.7rem', opacity: 0.8, flexShrink: 0 }}>
                              v{item.current_version || 1}
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
                              {item.execution_count && item.execution_count > 0 ? (
                                <>
                                  {item.last_execution_success ? (
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
                                  {item.execution_count} run{item.execution_count > 1 ? 's' : ''}
                                </>
                              ) : (
                                'Never executed'
                              )}
                            </Typography>
                          </>
                        )}
                        
                        {/* Tags */}
                        {item.tags && item.tags.length > 0 && (
                          <>
                            <Typography variant="body2" sx={{ opacity: 0.5, flexShrink: 0 }}>•</Typography>
                            <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                              {item.tags.slice(0, 2).map(tagName => {
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
                              {item.tags.length > 2 && (
                                <Typography variant="caption" sx={{ fontSize: '0.65rem', opacity: 0.7 }}>
                                  +{item.tags.length - 2}
                                </Typography>
                              )}
                            </Box>
                          </>
                        )}
                        
                        {/* Delete Button (Test Cases only) */}
                        {isTestCase && onDelete && (
                          <IconButton
                            size="small"
                            onClick={(e) => handleDeleteClick(e, item)}
                            sx={{
                              p: 0.5,
                              ml: 'auto',
                              flexShrink: 0,
                              color: isSelected ? 'primary.contrastText' : 'error.main',
                              '&:hover': {
                                bgcolor: isSelected ? 'rgba(255,255,255,0.2)' : 'error.light'
                              },
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
          {filteredItems.length} item{filteredItems.length !== 1 ? 's' : ''}
          {selectedType && selectedType !== 'All' && ` • ${selectedType}`}
          {selectedFolder && selectedFolder !== 'All' && ` in ${selectedFolder}`}
          {selectedTags.length > 0 && ` • ${selectedTags.join(', ')}`}
          {searchQuery && ` • "${searchQuery}"`}
        </Typography>
        {(searchQuery || selectedTags.length > 0 || (selectedFolder && selectedFolder !== 'All') || (selectedType && selectedType !== 'All')) && (
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer', textDecoration: 'underline', fontSize: '0.75rem' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedTags([]);
              setSelectedFolder('All');
              setSelectedType('All');
            }}
          >
            Clear filters
          </Typography>
        )}
      </Box>
    </Box>
  );
});
