import React from 'react';
import { Box, Button, Typography } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import AddIcon from '@mui/icons-material/Add';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { UserinterfaceSelector } from '../../common/UserinterfaceSelector';
import { NavigationEditorDeviceControls } from '../../navigation/Navigation_NavigationEditor_DeviceControls';

interface TestCaseBuilderHeaderProps {
  // Theme
  actualMode: 'light' | 'dark';
  
  // Creation Mode
  creationMode: 'visual' | 'ai';
  setCreationMode: (mode: 'visual' | 'ai') => void;
  
  // Device & Host
  selectedHost: any;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  isControlLoading: boolean;
  isRemotePanelOpen: boolean;
  availableHosts: any[];
  isDeviceLocked: (deviceKey: string) => boolean;
  handleDeviceSelect: (host: any, deviceId: string) => void;
  handleDeviceControl: (host: any, deviceId: string) => void;
  handleToggleRemotePanel: () => void;
  
  // Interface
  compatibleInterfaceNames: string[];
  userinterfaceName: string;
  setUserinterfaceName: (name: string) => void;
  
  // Test Case
  testcaseName: string;
  hasUnsavedChanges: boolean;
  currentTestcaseId: string | null;
  
  // Actions
  handleNew: () => void;
  setLoadDialogOpen: (open: boolean) => void;
  setSaveDialogOpen: (open: boolean) => void;
  handleExecute: () => void;
  
  // Execution State
  isExecuting: boolean;
}

export const TestCaseBuilderHeader: React.FC<TestCaseBuilderHeaderProps> = ({
  actualMode,
  creationMode,
  setCreationMode,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  isControlLoading,
  isRemotePanelOpen,
  availableHosts,
  isDeviceLocked,
  handleDeviceSelect,
  handleDeviceControl,
  handleToggleRemotePanel,
  compatibleInterfaceNames,
  userinterfaceName,
  setUserinterfaceName,
  testcaseName,
  hasUnsavedChanges,
  currentTestcaseId,
  handleNew,
  setLoadDialogOpen,
  setSaveDialogOpen,
  handleExecute,
  isExecuting,
}) => {
  return (
    <Box
      sx={{
        px: 2,
        py: 0,
        borderBottom: 1,
        borderColor: 'divider',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: actualMode === 'dark' ? '#111827' : '#ffffff',
        height: '46px',
        flexShrink: 0,
      }}
    >
      {/* SECTION 1: Title */}
      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 240px' }}>
        <Typography variant="h6" fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
          TestCase Builder
        </Typography>
      </Box>
      
      {/* SECTION 2: Visual/AI Mode Toggle */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: '0 0 auto', ml: 2 }}>
        <Button
          size="small"
          variant={creationMode === 'visual' ? 'contained' : 'outlined'}
          onClick={() => setCreationMode('visual')}
          sx={{ fontSize: 11, py: 0.5, px: 1.5 }}
        >
          Visual
        </Button>
        <Button
          size="small"
          variant={creationMode === 'ai' ? 'contained' : 'outlined'}
          onClick={() => setCreationMode('ai')}
          startIcon={<AutoAwesomeIcon fontSize="small" />}
          sx={{ fontSize: 11, py: 0.5, px: 1.5 }}
        >
          AI
        </Button>
      </Box>
      
      {/* SECTION 2.5: Device Control */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: '0 0 auto', ml: 2, borderLeft: 1, borderColor: 'divider', pl: 2 }}>
        <NavigationEditorDeviceControls
          selectedHost={selectedHost}
          selectedDeviceId={selectedDeviceId}
          isControlActive={isControlActive}
          isControlLoading={isControlLoading}
          isRemotePanelOpen={isRemotePanelOpen}
          availableHosts={availableHosts}
          isDeviceLocked={isDeviceLocked}
          onDeviceSelect={handleDeviceSelect}
          onTakeControl={handleDeviceControl}
          onToggleRemotePanel={handleToggleRemotePanel}
        />
      </Box>
      
      {/* SECTION 3: Interface Selector */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0, flex: '0 1 auto', ml: 0, justifyContent: 'center' }}>
        <UserinterfaceSelector
          compatibleInterfaces={compatibleInterfaceNames}
          value={userinterfaceName}
          onChange={setUserinterfaceName}
          label="Interface"
          size="small"
          fullWidth={false}
          sx={{ minWidth: 180}}
          disabled={!selectedDeviceId || !isControlActive}
        />
      </Box>
      
      {/* SECTION 4: TestCase Info + Action Buttons */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minWidth: 0, flex: '0 0 auto', ml: 2 }}>
        {testcaseName && (
          <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
            {testcaseName}{hasUnsavedChanges ? ' *' : ''} {currentTestcaseId ? '(saved)' : '(unsaved)'}
          </Typography>
        )}
        
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button 
            size="small" 
            variant="outlined" 
            startIcon={<AddIcon />} 
            onClick={handleNew}
            disabled={!userinterfaceName}
            title={!userinterfaceName ? 'Select a userinterface first' : 'Create new test case'}
          >
            New
          </Button>
          <Button 
            size="small" 
            variant="outlined" 
            startIcon={<FolderOpenIcon />} 
            onClick={() => setLoadDialogOpen(true)}
            disabled={!selectedDeviceId || !isControlActive}
            title={
              !selectedDeviceId ? 'Select a device first' :
              !isControlActive ? 'Take control of device first' :
              'Load saved test case'
            }
          >
            Load
          </Button>
          <Button 
            size="small" 
            variant="outlined" 
            startIcon={<SaveIcon />} 
            onClick={() => setSaveDialogOpen(true)}
            disabled={!userinterfaceName || !hasUnsavedChanges}
            title={
              !userinterfaceName ? 'Select a userinterface first' : 
              !hasUnsavedChanges ? 'No unsaved changes' :
              'Save test case'
            }
          >
            Save
          </Button>
          <Button
            size="small"
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={handleExecute}
            disabled={
              isExecuting || 
              !selectedDeviceId || 
              !isControlActive || 
              !userinterfaceName
            }
            title={
              !userinterfaceName ? 'Select a userinterface first' :
              !selectedDeviceId ? 'Select a device first' :
              !isControlActive ? 'Take control of device first' :
              isExecuting ? 'Test is running' :
              'Run test case on device'
            }
          >
            {isExecuting ? 'Running...' : 'Run'}
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

