/**
 * Enhanced Device Control Hook with Force Unlock
 * 
 * Wraps useDeviceControl with additional force unlock logic.
 * Used by NavigationEditor and TestCaseBuilder to avoid code duplication.
 */

import { useCallback } from 'react';
import { useDeviceControl } from './useDeviceControl';
import { useToast } from './useToast';
import { useConfirmDialog } from './useConfirmDialog';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface UseDeviceControlWithForceUnlockProps {
  host: any;
  device_id: string | null;
  sessionId: string;
  autoCleanup?: boolean;
  tree_id?: string; // Navigation tree ID for cache population
  requireTreeId?: boolean; // If true, requires tree_id to take control (default: false)
  onControlStateChange?: (active: boolean) => void;
}

interface UseDeviceControlWithForceUnlockReturn {
  isControlActive: boolean;
  isControlLoading: boolean;
  controlError: string | null;
  handleDeviceControl: () => Promise<void>;
  clearError: () => void;
  confirmDialogState: any;
  confirmDialogHandleConfirm: () => void;
  confirmDialogHandleCancel: () => void;
}

/**
 * Enhanced device control hook with force unlock capability
 */
export const useDeviceControlWithForceUnlock = ({
  host,
  device_id,
  sessionId,
  autoCleanup = true,
  tree_id,
  requireTreeId = false, // Default: tree_id is optional
  onControlStateChange,
}: UseDeviceControlWithForceUnlockProps): UseDeviceControlWithForceUnlockReturn => {
  
  const { showError } = useToast();
  
  // Confirmation dialog for force unlock
  const { dialogState, confirm, handleConfirm, handleCancel } = useConfirmDialog();
  
  const {
    isControlActive,
    isControlLoading,
    controlError,
    handleTakeControl,
    handleReleaseControl,
    clearError,
  } = useDeviceControl({
    host,
    device_id: device_id || 'device1',
    sessionId,
    autoCleanup,
    tree_id,
  });

  /**
   * Handle device control with force unlock logic
   */
  const handleDeviceControl = useCallback(async () => {
    if (isControlActive) {
      // Release device control
      console.log('[@useDeviceControlWithForceUnlock] Releasing device control');
      const success = await handleReleaseControl();
      if (success && onControlStateChange) {
        onControlStateChange(false);
      }
    } else {
      // Validate tree_id only if required (e.g., for navigation-based workflows)
      if (requireTreeId && !tree_id) {
        const errorMsg = 'Cannot take control: Please select a userinterface first. The navigation cache requires a valid tree_id.';
        console.error('[@useDeviceControlWithForceUnlock] ❌ Validation failed: tree_id is missing (required)');
        showError(errorMsg);
        return;
      }
      
      // Take device control (tree_id is optional - backend handles it)
      const treeIdMsg = tree_id ? `with tree_id: ${tree_id}` : 'without tree_id (cache skipped)';
      console.log(`[@useDeviceControlWithForceUnlock] ✅ Taking device control ${treeIdMsg}`);
      const result = await handleTakeControl();
      
      // If take control succeeded
      if (result.success) {
        if (onControlStateChange) {
          onControlStateChange(true);
        }
        return;
      }
      
      // If failed due to device lock, offer force unlock
      if (result.errorType === 'device_locked' && host) {
        confirm({
          title: 'Device Locked',
          message: 
            `Device ${host.host_name} is currently locked by another session.\n\n` +
            `This might be your own session from a different browser or Wi-Fi network.\n\n` +
            `Do you want to force release the lock and take control?`,
          confirmColor: 'warning',
          confirmText: 'Force Unlock',
          cancelText: 'Cancel',
          onConfirm: async () => {
            console.log('[@useDeviceControlWithForceUnlock] User confirmed force takeover');
            
            // Call force unlock API
            try {
              const response = await fetch(buildServerUrl('/server/control/forceUnlock'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host_name: host.host_name }),
              });
              
              const unlockResult = await response.json();
              
              if (unlockResult.success) {
                console.log('[@useDeviceControlWithForceUnlock] Force unlock successful, retrying take control');
                
                // Retry take control
                const retryResult = await handleTakeControl();
                if (retryResult.success && onControlStateChange) {
                  onControlStateChange(true);
                }
              } else {
                showError(`Failed to force unlock: ${unlockResult.error || 'Unknown error'}`);
              }
            } catch (error: any) {
              showError(`Failed to force unlock: ${error.message || 'Unknown error'}`);
            }
          },
        });
      }
    }
  }, [
    isControlActive,
    handleTakeControl,
    handleReleaseControl,
    onControlStateChange,
    host,
    showError,
    tree_id,
    confirm,
  ]);

  return {
    isControlActive,
    isControlLoading,
    controlError,
    handleDeviceControl,
    clearError,
    confirmDialogState: dialogState,
    confirmDialogHandleConfirm: handleConfirm,
    confirmDialogHandleCancel: handleCancel,
  };
};

