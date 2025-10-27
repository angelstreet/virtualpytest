import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, TextField, Autocomplete, Chip, Typography, CircularProgress, Paper,
  List, ListItem, ListItemButton, InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon, Folder as FolderIcon,
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface ExecutableItem {
  type: 'script' | 'testcase';
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  userinterface?: string;
}

export interface UnifiedExecutableSelectorProps {
  value: ExecutableItem | null;
  onChange: (item: ExecutableItem) => void;
  label?: string;
  placeholder?: string;
  filters?: {
    search?: boolean;
    folders?: boolean;
    tags?: boolean;
  };
  allowedTypes?: ('script' | 'testcase')[];
  collapseIcon?: React.ReactNode;
}

export const UnifiedExecutableSelector: React.FC<UnifiedExecutableSelectorProps> = ({
  value,
  onChange,
  placeholder = 'Search by name...',
  filters = { folders: true, tags: true, search: true },
  allowedTypes,
  collapseIcon,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allItems, setAllItems] = useState<ExecutableItem[]>([]);
  const [allFolderNames, setAllFolderNames] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<Array<{ name: string; color: string }>>([]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>('All');

  // Load executables on mount
  useEffect(() => {
    console.log('[@UnifiedExecutableSelector] Component mounted, loading executables...');
    loadExecutables();
  }, []);

  const loadExecutables = async () => {
    try {
      console.log('[@UnifiedExecutableSelector] Loading executables from API...');
      setLoading(true);
      setError(null);

      const response = await fetch(buildServerUrl('/server/executable/list'));
      const data = await response.json();

      console.log('[@UnifiedExecutableSelector] API response:', {
        success: data.success,
        foldersCount: data.folders?.length,
      });

      if (data.success) {
        // Flatten all items from all folders
        const items: ExecutableItem[] = [];
        data.folders.forEach((folder: any) => {
          folder.items.forEach((item: any) => {
            items.push({
              ...item,
              folder: folder.name, // Add folder info to each item
            });
          });
        });

        setAllItems(items);
        setAllFolderNames(data.all_folders || []);
        setAllTags(data.all_tags || []);
        console.log('[@UnifiedExecutableSelector] ✅ Loaded', items.length, 'items');
      } else {
        throw new Error(data.error || 'Failed to load executables');
      }
    } catch (err) {
      console.error('[@UnifiedExecutableSelector] ❌ Error loading executables:', err);
      setError(err instanceof Error ? err.message : 'Failed to load executables');
    } finally {
      setLoading(false);
      console.log('[@UnifiedExecutableSelector] Loading complete');
    }
  };

  // Filter items
  const filteredItems = useMemo(() => {
    let items = [...allItems];

    // Apply type filter
    if (allowedTypes && allowedTypes.length > 0) {
      items = items.filter(item => allowedTypes.includes(item.type));
    }

    // Apply folder filter
    if (selectedFolder && selectedFolder !== 'All') {
      items = items.filter((item: any) => item.folder === selectedFolder);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      items = items.filter(item =>
        item.name.toLowerCase().includes(query) ||
        item.description?.toLowerCase().includes(query)
      );
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      items = items.filter(item =>
        item.tags && item.tags.some(tag => selectedTags.includes(tag))
      );
    }

    return items;
  }, [allItems, searchQuery, selectedTags, selectedFolder, allowedTypes]);

  // Handle item selection
  const handleItemSelect = (item: ExecutableItem) => {
    console.log('[@UnifiedExecutableSelector] 🎯 Item selected:', item.name);
    onChange(item);
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
      {/* Filters Section - All in one row, equal sizes, with collapse icon on right */}
      <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
        {filters.search && (
          <TextField
            size="small"
            placeholder={placeholder}
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
        )}

        {filters.folders && (
          <Autocomplete
            size="small"
            value={selectedFolder}
            onChange={(_event, newValue) => setSelectedFolder(newValue)}
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
              />
            )}
            sx={{ flex: 1 }}
          />
        )}

        {filters.tags && (
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
              />
            )}
            sx={{ flex: 1 }}
          />
        )}

        {/* Collapse icon on the right */}
        {collapseIcon && (
          <Box sx={{ flexShrink: 0 }}>
            {collapseIcon}
          </Box>
        )}
      </Box>

      {/* Flat Item List - Full width */}
      <Box>
          <Paper variant="outlined" sx={{ maxHeight: 200, overflow: 'auto' }}>
            {filteredItems.length === 0 ? (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  No executables found
                </Typography>
              </Box>
            ) : (
              <List dense disablePadding>
                {filteredItems.map(item => {
                  const isSelected = value?.id === item.id;
                  return (
                    <ListItem
                      key={item.id}
                      disablePadding
                      sx={{
                        bgcolor: isSelected ? 'primary.main' : 'transparent',
                        '&:hover': { bgcolor: isSelected ? 'primary.dark' : 'action.hover' },
                        borderLeft: isSelected ? '3px solid' : 'none',
                        borderColor: 'primary.light'
                      }}
                    >
                      <ListItemButton
                        onClick={() => handleItemSelect(item)}
                        selected={isSelected}
                        sx={{
                          py: 0.25,
                          pl: isSelected ? 0.75 : 1,
                          pr: 1,
                          minHeight: 28,
                          color: isSelected ? 'primary.contrastText' : 'inherit'
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, width: '100%' }}>
                          <Chip
                            label={item.type === 'script' ? 'S' : 'TC'}
                            size="small"
                            color={item.type === 'script' ? 'primary' : 'secondary'}
                            sx={{
                              height: '16px',
                              fontSize: '0.6rem',
                              minWidth: '24px',
                              '.MuiChip-label': { px: 0.5 },
                              bgcolor: isSelected ? 'rgba(255,255,255,0.9)' : undefined,
                              color: isSelected ? 'primary.main' : undefined
                            }}
                          />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '0.8rem',
                              flex: 1,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              fontWeight: isSelected ? 'bold' : 'normal'
                            }}
                          >
                            {item.name}
                          </Typography>
                          {item.tags && item.tags.length > 0 && (
                            <Box sx={{ display: 'flex', gap: 0.25 }}>
                              {item.tags.map(tagName => {
                                const tag = allTags.find(t => t.name === tagName);
                                return (
                                  <Chip
                                    key={tagName}
                                    label={tagName}
                                    size="small"
                                    sx={{
                                      height: '14px',
                                      fontSize: '0.55rem',
                                      backgroundColor: isSelected ? 'rgba(255,255,255,0.9)' : (tag?.color || '#9e9e9e'),
                                      color: isSelected ? 'primary.main' : 'white'
                                    }}
                                  />
                                );
                              })}
                            </Box>
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

      {/* Summary - Compact */}
      <Box sx={{ mt: 0.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
          {filteredItems.length} items
          {selectedFolder && selectedFolder !== 'All' && ` in ${selectedFolder}`}
          {selectedTags.length > 0 && ` • ${selectedTags.join(', ')}`}
          {searchQuery && ` • "${searchQuery}"`}
        </Typography>
        {(searchQuery || selectedTags.length > 0 || selectedFolder) && (
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer', textDecoration: 'underline', fontSize: '0.7rem' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedTags([]);
              setSelectedFolder(null);
            }}
          >
            Clear
          </Typography>
        )}
      </Box>
    </Box>
  );
};

