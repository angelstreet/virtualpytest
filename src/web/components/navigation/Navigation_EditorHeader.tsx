import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import React from 'react';

import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { useNavigationStack } from '../../contexts/navigation/NavigationStackContext';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import { useHostManager } from '../../hooks/useHostManager';
import { useToast } from '../../hooks/useToast';

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
}) => {
  // Get toast notifications
  const { showError } = useToast();

  // Get navigation context for current position updates
  const { updateCurrentPosition } = useNavigation();

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
      await handleTakeControl();
    }
  }, [isControlActive, handleTakeControl, handleReleaseControl, resetCurrentNodeId]);

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
        <Toolbar variant="dense" sx={{ minHeight: 48, px: 2 }}>
          {/* Grid Layout with 4 sections */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: '60px 360px 300px 340px',
              gap: 1,
              alignItems: 'center',
              width: '100%',
            }}
          >
            {/* Section 1: Tree Name and Status */}
            <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
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

            {/* Section 3: Action Buttons */}
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
            />

            {/* Section 4: Device Controls - now with proper device-oriented locking */}
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
          </Box>
        </Toolbar>
      </AppBar>

      {/* Validation components are now rendered by ValidationButtonClient when needed */}
    </>
  );
};

export default NavigationEditorHeader;
