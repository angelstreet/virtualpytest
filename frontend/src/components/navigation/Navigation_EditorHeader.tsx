import { AppBar, Toolbar, Typography, Box, Button } from '@mui/material';
import { SmartToy as SmartToyIcon } from '@mui/icons-material';
import React from 'react';

import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { useNavigationStack } from '../../contexts/navigation/NavigationStackContext';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import { useHostManager } from '../../hooks/useHostManager';
import { useToast } from '../../hooks/useToast';
import { buildServerUrl } from '../../utils/buildUrlUtils';

import NavigationEditorActionButtons from './Navigation_NavigationEditor_ActionButtons';
import NavigationEditorDeviceControls from './Navigation_NavigationEditor_DeviceControls';
import NavigationEditorTreeControls from './Navigation_NavigationEditor_TreeControls';

export const NavigationEditorHeader: React.FC<{
  hasUnsavedChanges: boolean;
  focusNodeId: string | null;
  availableFocusNodes: any[];
  maxDisplayDepth: number;
  totalNodes: number;
  visibleNodes: number;
  isLoading: boolean;
  error: string | null;
  isLocked: boolean;
  treeId: string;
  selectedHost: any; // Full host object
  selectedDeviceId?: string | null; // Selected device ID
  isRemotePanelOpen: boolean;
  // Host data (filtered by interface models)
  availableHosts: any[];

  onAddNewNode: () => void;
  onFitView: () => void;
  onSaveToConfig: () => void;
  onDiscardChanges: () => void;
  onFocusNodeChange: (nodeId: string | null) => void;
  onDepthChange: (depth: number) => void;
  onResetFocus: () => void;
  onToggleRemotePanel: () => void;
  onControlStateChange: (active: boolean) => void;
  onDeviceSelect: (host: any, deviceId: string | null) => void;
  onUpdateNode?: (nodeId: string, updatedData: any) => void;
  onUpdateEdge?: (edgeId: string, updatedData: any) => void;
  onToggleAIGeneration?: () => void;
}> = ({
  hasUnsavedChanges,
  focusNodeId,
  availableFocusNodes,
  maxDisplayDepth,
  totalNodes,
  visibleNodes,
  isLoading,
  error,
  isLocked,
  treeId,
  selectedHost,
  selectedDeviceId,
  isRemotePanelOpen,
  // Host data (filtered by interface models)
  availableHosts,
  onAddNewNode,
  onFitView,
  onSaveToConfig,
  onDiscardChanges,
  onFocusNodeChange,
  onDepthChange,
  onResetFocus,
  onToggleRemotePanel,
  onControlStateChange,
  onDeviceSelect,
  onToggleAIGeneration,
}) => {
  // Get toast notifications
  const { showError } = useToast();

  // Get navigation context for current position updates and undo/redo
  const { updateCurrentPosition, undo, redo, canUndo, canRedo } = useNavigation();

  // Get navigation stack for breadcrumb display
  const { isNested, currentLevel } = useNavigationStack();

  // Get device locking functionality from HostManager
  const { isDeviceLocked } = useHostManager();

  // Device control hook (physical device control)
  const {
    isControlActive,
    isControlLoading,
    controlError,
    handleTakeControl,
    handleReleaseControl,
    clearError,
  } = useDeviceControl({
    host: selectedHost,
    device_id: selectedDeviceId || 'device1', // Pass device_id for device-oriented control
    sessionId: 'navigation-editor-session',
    autoCleanup: true, // Auto-release on unmount
    tree_id: treeId, // Pass tree_id for navigation cache population
  });

  // Function to reset current node ID
  const resetCurrentNodeId = React.useCallback(() => {
    console.log('[@component:NavigationEditorHeader] Resetting current node ID');
    updateCurrentPosition(null, null);
  }, [updateCurrentPosition]);

  // Enhanced reset focus handler that also resets current node ID
  const handleResetFocus = React.useCallback(() => {
    console.log('[@component:NavigationEditorHeader] Resetting focus and current node ID');
    onResetFocus(); // Reset the focus/filter
    resetCurrentNodeId(); // Reset the current node ID
  }, [onResetFocus, resetCurrentNodeId]);

  // Device control handler (only controls physical device, not navigation tree)
  const handleDeviceControl = React.useCallback(async () => {
    if (isControlActive) {
      // Release device control only
      console.log('[@component:NavigationEditorHeader] Releasing device control');
      await handleReleaseControl();
      // Reset current node ID when control is released
      resetCurrentNodeId();
    } else {
      // Take device control only
      console.log('[@component:NavigationEditorHeader] Taking device control');
      const success = await handleTakeControl();
      
      // If take control failed due to lock, check if we should force unlock
      if (!success && controlError && controlError.includes('in use')) {
        const confirmed = window.confirm(
          `Device ${selectedHost?.host_name} is currently locked by another session.\n\n` +
          `This might be your own session from a different browser or Wi-Fi network.\n\n` +
          `Do you want to force release the lock and take control?`
        );
        
        if (confirmed && selectedHost) {
          console.log('[@component:NavigationEditorHeader] User confirmed force takeover');
          // Call force unlock API
          try {
            const response = await fetch(buildServerUrl('/server/control/forceUnlock'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ host_name: selectedHost.host_name }),
            });
            
            const result = await response.json();
            
            if (result.success) {
              console.log('[@component:NavigationEditorHeader] Force unlock successful, retrying take control');
              // Retry take control
              await handleTakeControl();
            } else {
              showError(`Failed to force unlock: ${result.error || 'Unknown error'}`);
            }
          } catch (error: any) {
            showError(`Failed to force unlock: ${error.message || 'Unknown error'}`);
          }
        }
      }
    }
  }, [isControlActive, handleTakeControl, handleReleaseControl, resetCurrentNodeId, controlError, selectedHost, showError]);

  // Sync control state with parent component (only device control)
  React.useEffect(() => {
    onControlStateChange(isControlActive);
  }, [isControlActive, onControlStateChange]);

  // Show control errors
  React.useEffect(() => {
    if (controlError) {
      showError(controlError);
      clearError();
    }
  }, [controlError, showError, clearError]);

  // Debug logging for device selection changes
  React.useEffect(() => {
    if (selectedHost && selectedDeviceId) {
      const device = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
      if (device) {
        console.log(
          `[@component:NavigationEditorHeader] Device selected: ${device.device_name} (${device.device_model}) on host ${selectedHost.host_name}`,
        );
      }
    }
  }, [selectedHost, selectedDeviceId]);

  return (
    <>
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar variant="dense" sx={{ minHeight: 44, px: 2 }}>
          {/* Flex Layout with 4 sections - responsive */}
          <Box
            sx={{
              display: 'flex',
              gap: 2,
              alignItems: 'center',
              width: '100%',
              justifyContent: 'space-between',
            }}
          >
            {/* Section 1: Tree Name and Status */}
            <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 auto' }}>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 'medium',
                  color: 'text.primary',
                  fontSize: '1rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {isNested ? currentLevel?.treeName || 'Sub-tree' : 'root'}
                {hasUnsavedChanges && (
                  <Typography component="span" sx={{ color: 'warning.main', ml: 0.5 }}>
                    *
                  </Typography>
                )}
              </Typography>
            </Box>

            {/* Section 2: Tree Controls */}
            <Box sx={{ flex: '0 1 auto', minWidth: 0 }}>
              <NavigationEditorTreeControls
                focusNodeId={focusNodeId}
                availableFocusNodes={availableFocusNodes}
                maxDisplayDepth={maxDisplayDepth}
                totalNodes={totalNodes}
                visibleNodes={visibleNodes}
                onFocusNodeChange={onFocusNodeChange}
                onDepthChange={onDepthChange}
                onResetFocus={handleResetFocus}
              />
            </Box>

            {/* Section 3: Action Buttons */}
            <Box sx={{ flex: '0 1 auto', minWidth: 0 }}>
              <NavigationEditorActionButtons
              treeId={treeId}
              isLocked={isLocked}
              hasUnsavedChanges={hasUnsavedChanges}
              isLoading={isLoading}
              error={error}
              selectedHost={selectedHost}
              selectedDeviceId={selectedDeviceId || null}
              isControlActive={isControlActive}
              onAddNewNode={onAddNewNode}
              onFitView={onFitView}
              onSaveToConfig={onSaveToConfig}
              onDiscardChanges={onDiscardChanges}
              onUndo={undo}
              onRedo={redo}
              canUndo={canUndo}
              canRedo={canRedo}
            />
            </Box>

            {/* Section 4: Device Controls - now with proper device-oriented locking */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: '0 0 auto' }}>
              <NavigationEditorDeviceControls
                selectedHost={selectedHost}
                selectedDeviceId={selectedDeviceId || null}
                isControlActive={isControlActive}
                isControlLoading={isControlLoading}
                isRemotePanelOpen={isRemotePanelOpen}
                availableHosts={availableHosts}
                isDeviceLocked={(deviceKey: string) => {
                  // Parse deviceKey format: "hostname:device_id"
                  const [hostName, deviceId] = deviceKey.includes(':')
                    ? deviceKey.split(':')
                    : [deviceKey, 'device1'];

                  const host = availableHosts.find((h) => h.host_name === hostName);
                  return isDeviceLocked(host, deviceId);
                }}
                onDeviceSelect={onDeviceSelect}
                onTakeControl={handleDeviceControl}
                onToggleRemotePanel={onToggleRemotePanel}
              />
              
              {/* AI Generate Button - Only show when control is active */}
              {isControlActive && selectedHost && selectedDeviceId && onToggleAIGeneration && (
                <Button
                  variant="outlined"
                  startIcon={<SmartToyIcon />}
                  onClick={onToggleAIGeneration}
                  size="small"
                  sx={{ minWidth: 'auto', whiteSpace: 'nowrap' }}
                >
                  AI
                </Button>
              )}
            </Box>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Validation components are now rendered by ValidationButtonClient when needed */}
    </>
  );
};

export default NavigationEditorHeader;
