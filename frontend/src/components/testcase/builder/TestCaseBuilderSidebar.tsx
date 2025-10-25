import React from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { TestCaseToolbox } from './TestCaseToolbox';
import { AIModePanel } from '../ai/AIModePanel';

interface TestCaseBuilderSidebarProps {
  actualMode: 'light' | 'dark';
  creationMode: 'visual' | 'ai';
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  
  // Toolbox Props
  categoryTabs: any[];
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  currentSubTab: string;
  setCurrentSubTab: (subTab: string) => void;
  toolboxSearchQuery: string;
  setToolboxSearchQuery: (query: string) => void;
  onDragStart: (event: React.DragEvent<HTMLDivElement>, nodeType: string, data: any) => void;
}

export const TestCaseBuilderSidebar: React.FC<TestCaseBuilderSidebarProps> = ({
  actualMode,
  creationMode,
  isSidebarOpen,
  toggleSidebar,
  categoryTabs,
  currentTab,
  setCurrentTab,
  currentSubTab,
  setCurrentSubTab,
  toolboxSearchQuery,
  setToolboxSearchQuery,
  onDragStart,
}) => {
  return (
    <>
      {/* Sidebar (Toolbox or AI Mode Panel) */}
      <Box
        sx={{
          width: isSidebarOpen ? '280px' : '0px',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          borderRight: isSidebarOpen ? 1 : 0,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          background: actualMode === 'dark' ? '#0f172a' : '#f8f9fa',
          position: 'relative',
        }}
      >
        {isSidebarOpen && (
          <>
            {/* Sidebar Header */}
            <Box
              sx={{
                px: 2,
                py: 1.5,
                borderBottom: 1,
                borderColor: 'divider',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
              }}
            >
              <Typography variant="subtitle1" fontWeight="bold">
                {creationMode === 'visual' ? 'Toolbox' : 'AI Generator'}
              </Typography>
              <IconButton
                size="small"
                onClick={toggleSidebar}
                sx={{
                  color: 'text.secondary',
                  '&:hover': { color: 'primary.main' },
                }}
              >
                <ChevronLeftIcon />
              </IconButton>
            </Box>
            
            {/* Sidebar Content */}
            <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {creationMode === 'visual' ? (
                <TestCaseToolbox
                  categoryTabs={categoryTabs}
                  currentTab={currentTab}
                  setCurrentTab={setCurrentTab}
                  currentSubTab={currentSubTab}
                  setCurrentSubTab={setCurrentSubTab}
                  searchQuery={toolboxSearchQuery}
                  setSearchQuery={setToolboxSearchQuery}
                  onDragStart={onDragStart}
                />
              ) : (
                <AIModePanel />
              )}
            </Box>
          </>
        )}
      </Box>
      
      {/* Toggle Button (when sidebar is closed) */}
      {!isSidebarOpen && (
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: 10,
          }}
        >
          <IconButton
            onClick={toggleSidebar}
            sx={{
              borderRadius: '0 8px 8px 0',
              background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
              border: 1,
              borderLeft: 0,
              borderColor: 'divider',
              '&:hover': {
                background: actualMode === 'dark' ? '#334155' : '#f1f5f9',
              },
            }}
          >
            <ChevronRightIcon />
          </IconButton>
        </Box>
      )}
    </>
  );
};

