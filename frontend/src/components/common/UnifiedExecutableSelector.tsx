/**
 * Unified Executable Selector Component
 * 
 * Reusable component for selecting scripts or testcases with:
 * - Folder-based organization
 * - Tag filtering
 * - Real-time search
 * - Unified interface for both types
 * 
 * Used by: RunTests, RunCampaigns
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  TextField,
  Autocomplete,
  Chip,
  Typography,
  CircularProgress,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Collapse,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Terminal as ScriptIcon,
  Science as TestcaseIcon,
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface ExecutableItem {
  type: 'script' | 'testcase';
  id: string; // script filename or testcase UUID
  name: string; // display name
  description?: string;
  tags?: Array<{ name: string; color: string }>;
  userinterface?: string;
  folder?: string;
}

interface FolderGroup {
  id: number;
  name: string;
  items: ExecutableItem[];
}

interface UnifiedExecutableSelectorProps {
  value: ExecutableItem | null;
  onChange: (executable: ExecutableItem | null) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  filters?: {
    folders?: boolean;
    tags?: boolean;
    search?: boolean;
  };
  // Optional: Filter by type
  allowedTypes?: Array<'script' | 'testcase'>;
}

export const UnifiedExecutableSelector: React.FC<UnifiedExecutableSelectorProps> = ({
  value,
  onChange,
  label = 'Select Script or Test Case',
  placeholder = 'Search by name...',
  disabled = false,
  filters = { folders: true, tags: true, search: true },
  allowedTypes,
}) => {
  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [folders, setFolders] = useState<FolderGroup[]>([]);
  const [allTags, setAllTags] = useState<Array<{ name: string; color: string }>>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set([0])); // Root folder expanded by default
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  // Load executables on mount
  useEffect(() => {
    loadExecutables();
  }, []);

  const loadExecutables = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(buildServerUrl('/server/executable/list'));
      const data = await response.json();

      if (data.success) {
        setFolders(data.folders || []);
        setAllTags(data.all_tags || []);
      } else {
        throw new Error(data.error || 'Failed to load executables');
      }
    } catch (err) {
      console.error('[@component:UnifiedExecutableSelector] Error loading executables:', err);
      setError(err instanceof Error ? err.message : 'Failed to load executables');
    } finally {
      setLoading(false);
    }
  };

  // Flatten all items for autocomplete
  const allItems = useMemo(() => {
    let items: ExecutableItem[] = [];
    folders.forEach(folder => {
      items = [...items, ...folder.items];
    });
    
    // Filter by allowed types if specified
    if (allowedTypes && allowedTypes.length > 0) {
      items = items.filter(item => allowedTypes.includes(item.type));
    }
    
    return items;
  }, [folders, allowedTypes]);

  // Filter items based on search, tags, and folder
  const filteredFolders = useMemo(() => {
    return folders.map(folder => {
      let items = folder.items;

      // Filter by allowed types
      if (allowedTypes && allowedTypes.length > 0) {
        items = items.filter(item => allowedTypes.includes(item.type));
      }

      // Filter by folder selection
      if (selectedFolder && folder.name !== selectedFolder) {
        return { ...folder, items: [] };
      }

      // Filter by search query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        items = items.filter(item => 
          item.name.toLowerCase().includes(query) ||
          item.description?.toLowerCase().includes(query)
        );
      }

      // Filter by tags (AND logic: item must have ALL selected tags)
      if (selectedTags.length > 0) {
        items = items.filter(item => {
          const itemTagNames = item.tags?.map(t => t.name) || [];
          return selectedTags.every(tag => itemTagNames.includes(tag));
        });
      }

      return { ...folder, items };
    }).filter(folder => folder.items.length > 0); // Only show folders with items
  }, [folders, searchQuery, selectedTags, selectedFolder, allowedTypes]);

  // Toggle folder expansion
  const toggleFolder = (folderId: number) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  // Get icon for executable type
  const getExecutableIcon = (type: 'script' | 'testcase') => {
    return type === 'script' ? <ScriptIcon fontSize="small" /> : <TestcaseIcon fontSize="small" />;
  };

  // Render loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Render error state
  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Filters Section */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 2 }}>
        {/* Search */}
        {filters.search && (
          <TextField
            fullWidth
            size="small"
            placeholder={placeholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        )}

        {/* Folder Filter */}
        {filters.folders && (
          <Autocomplete
            size="small"
            options={folders.map(f => f.name)}
            value={selectedFolder}
            onChange={(_, newValue) => setSelectedFolder(newValue)}
            renderInput={(params) => (
              <TextField {...params} label="Filter by Folder" placeholder="All folders" />
            )}
            clearable
          />
        )}

        {/* Tag Filter */}
        {filters.tags && allTags.length > 0 && (
          <Autocomplete
            multiple
            size="small"
            options={allTags.map(t => t.name)}
            value={selectedTags}
            onChange={(_, newValue) => setSelectedTags(newValue)}
            renderTags={(value, getTagProps) =>
              value.map((tagName, index) => {
                const tag = allTags.find(t => t.name === tagName);
                return (
                  <Chip
                    label={tagName}
                    size="small"
                    {...getTagProps({ index })}
                    sx={{
                      backgroundColor: tag?.color || '#9e9e9e',
                      color: 'white',
                      '& .MuiChip-deleteIcon': { 
                        color: 'rgba(255, 255, 255, 0.7)', 
                        '&:hover': { color: 'white' } 
                      }
                    }}
                  />
                );
              })
            }
            renderInput={(params) => (
              <TextField {...params} label="Filter by Tags" placeholder="Select tags..." />
            )}
          />
        )}
      </Box>

      {/* Selected Value Display */}
      {value && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getExecutableIcon(value.type)}
            <Typography variant="body1" fontWeight="bold">{value.name}</Typography>
            {value.tags && value.tags.length > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5, ml: 1 }}>
                {value.tags.map(tag => (
                  <Chip
                    key={tag.name}
                    label={tag.name}
                    size="small"
                    sx={{
                      height: 20,
                      backgroundColor: tag.color,
                      color: 'white',
                      fontSize: '0.7rem'
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
          {value.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {value.description}
            </Typography>
          )}
        </Box>
      )}

      {/* Executable List (Folder Tree) */}
      <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto' }}>
        {filteredFolders.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No executables found matching your filters
            </Typography>
          </Box>
        ) : (
          <List dense>
            {filteredFolders.map(folder => {
              const isExpanded = expandedFolders.has(folder.id);
              
              return (
                <React.Fragment key={folder.id}>
                  {/* Folder Header */}
                  <ListItem disablePadding>
                    <ListItemButton onClick={() => toggleFolder(folder.id)}>
                      {isExpanded ? <FolderOpenIcon sx={{ mr: 1 }} /> : <FolderIcon sx={{ mr: 1 }} />}
                      <ListItemText 
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" fontWeight="bold">
                              {folder.name}
                            </Typography>
                            <Chip label={folder.items.length} size="small" />
                          </Box>
                        }
                      />
                      {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </ListItemButton>
                  </ListItem>

                  {/* Folder Items */}
                  <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      {folder.items.map(item => (
                        <ListItem 
                          key={item.id} 
                          disablePadding
                          sx={{
                            bgcolor: value?.id === item.id ? 'action.selected' : 'transparent'
                          }}
                        >
                          <ListItemButton 
                            sx={{ pl: 4 }}
                            onClick={() => onChange(item)}
                            selected={value?.id === item.id}
                          >
                            {getExecutableIcon(item.type)}
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 1 }}>
                                  <Typography variant="body2">{item.name}</Typography>
                                  {item.tags && item.tags.length > 0 && (
                                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                                      {item.tags.map(tag => (
                                        <Chip
                                          key={tag.name}
                                          label={tag.name}
                                          size="small"
                                          sx={{
                                            height: 18,
                                            fontSize: '0.65rem',
                                            backgroundColor: tag.color,
                                            color: 'white'
                                          }}
                                        />
                                      ))}
                                    </Box>
                                  )}
                                </Box>
                              }
                              secondary={item.description}
                            />
                          </ListItemButton>
                        </ListItem>
                      ))}
                    </List>
                  </Collapse>
                </React.Fragment>
              );
            })}
          </List>
        )}
      </Paper>

      {/* Summary */}
      <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          {filteredFolders.reduce((sum, f) => sum + f.items.length, 0)} items
          {selectedTags.length > 0 && ` with tags: ${selectedTags.join(', ')}`}
          {searchQuery && ` matching "${searchQuery}"`}
        </Typography>
        {(searchQuery || selectedTags.length > 0 || selectedFolder) && (
          <Typography
            variant="caption"
            color="primary"
            sx={{ cursor: 'pointer', textDecoration: 'underline' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedTags([]);
              setSelectedFolder(null);
            }}
          >
            Clear filters
          </Typography>
        )}
      </Box>
    </Box>
  );
};

