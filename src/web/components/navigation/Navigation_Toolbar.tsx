import {
  Add as AddIcon,
  FitScreen as FitScreenIcon,
  Cancel as CancelIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { AppBar, Toolbar, Typography, Button, IconButton, Box } from '@mui/material';
import React from 'react';

interface NavigationToolbarProps {
  // Navigation state
  navigationPath: string[];
  navigationNamePath: string[];
  viewPath: Array<{ name: string }>;
  hasUnsavedChanges: boolean;

  // Loading and error state
  isLoading: boolean;
  error: string | null;

  // History state removed - using page reload for cancel changes

  // Event handlers
  navigateToParent: () => void;
  navigateToTreeLevel: (index: number) => void;
  navigateToParentView: (index: number) => void;
  addNewNode: () => void;
  fitView: () => void;
  // undo/redo removed - using page reload for cancel changes
  discardChanges: () => void;
}

export const NavigationToolbar: React.FC<NavigationToolbarProps> = ({
  navigationPath,
  navigationNamePath,
  viewPath,
  hasUnsavedChanges,
  isLoading,
  error,
  // History props removed
  navigateToParent,
  navigateToTreeLevel,
  navigateToParentView,
  addNewNode,
  fitView,
  // undo/redo functions removed
  discardChanges,
}) => {
  return (
    <AppBar position="static" color="default" elevation={1}>
      <Toolbar variant="dense" sx={{ minHeight: 48 }}>
        {/* Only show back button if not at root level */}
        {navigationPath.length > 1 && (
          <IconButton
            edge="start"
            onClick={navigateToParent}
            size="small"
            title="Back to Trees"
            sx={{ mr: 1 }}
          >
            <ArrowBackIcon />
          </IconButton>
        )}

        {/* Breadcrumb navigation */}
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          {/* Tree level breadcrumb */}
          {navigationNamePath.map((treeName, index) => (
            <Box key={`tree-${index}`} sx={{ display: 'flex', alignItems: 'center' }}>
              {index > 0 && (
                <Typography variant="h6" sx={{ mx: 0.5, color: 'text.secondary' }}>
                  &gt;
                </Typography>
              )}
              <Button
                variant="text"
                size="small"
                onClick={() => navigateToTreeLevel(index)}
                sx={{
                  textTransform: 'none',
                  minWidth: 'auto',
                  fontWeight: 'normal',
                  color: 'text.secondary',
                }}
              >
                {decodeURIComponent(treeName)}
              </Button>
            </Box>
          ))}

          {/* View level breadcrumb */}
          {viewPath.length > 1 &&
            viewPath.map((level, index) => (
              <Box key={`view-${index}`} sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="h6" sx={{ mx: 0.5, color: 'text.secondary' }}>
                  &gt;
                </Typography>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => navigateToParentView(index)}
                  sx={{
                    textTransform: 'none',
                    minWidth: 'auto',
                    fontWeight: index === viewPath.length - 1 ? 'bold' : 'normal',
                    color: index === viewPath.length - 1 ? 'primary.main' : 'text.secondary',
                  }}
                >
                  {level.name}
                  {index === viewPath.length - 1 && hasUnsavedChanges && (
                    <Typography component="span" sx={{ color: 'warning.main', ml: 0.5 }}>
                      *
                    </Typography>
                  )}
                </Button>
              </Box>
            ))}
        </Box>

        <Button
          startIcon={<AddIcon />}
          onClick={addNewNode}
          size="small"
          sx={{ mr: 1 }}
          disabled={isLoading || !!error}
        >
          Add Screen
        </Button>

        <Typography
          variant="caption"
          sx={{
            mr: 2,
            color: 'text.secondary',
            fontSize: '0.7rem',
            display: { xs: 'none', md: 'block' },
          }}
        ></Typography>

        <IconButton onClick={fitView} size="small" title="Fit View" disabled={isLoading || !!error}>
          <FitScreenIcon />
        </IconButton>

        {/* Undo/Redo buttons removed - using page reload for cancel changes */}

        <IconButton
          onClick={discardChanges}
          size="small"
          title={hasUnsavedChanges ? 'Discard Unsaved Changes' : 'Discard Changes'}
          color={hasUnsavedChanges ? 'warning' : 'default'}
          disabled={isLoading || !!error}
        >
          <CancelIcon />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
};
