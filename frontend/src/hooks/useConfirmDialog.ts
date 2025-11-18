import { useState, useCallback } from 'react';

interface ConfirmDialogState {
  open: boolean;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  confirmColor: 'primary' | 'error' | 'warning' | 'info' | 'success';
  onConfirm: () => void;
}

const DEFAULT_STATE: ConfirmDialogState = {
  open: false,
  title: 'Confirm Action',
  message: '',
  confirmText: 'OK',
  cancelText: 'Cancel',
  confirmColor: 'primary',
  onConfirm: () => {},
};

/**
 * Hook to manage confirmation dialog state
 * Provides a replacement for window.confirm() with Material-UI styling
 * 
 * Usage:
 * ```tsx
 * const { dialogState, confirm, handleConfirm, handleCancel } = useConfirmDialog();
 * 
 * // In your component JSX:
 * <ConfirmDialog
 *   open={dialogState.open}
 *   title={dialogState.title}
 *   message={dialogState.message}
 *   confirmText={dialogState.confirmText}
 *   cancelText={dialogState.cancelText}
 *   confirmColor={dialogState.confirmColor}
 *   onConfirm={handleConfirm}
 *   onCancel={handleCancel}
 * />
 * 
 * // To show the dialog:
 * confirm({
 *   title: 'Delete Item',
 *   message: 'Are you sure you want to delete this item?',
 *   confirmColor: 'error',
 *   onConfirm: () => deleteItem(id)
 * });
 * ```
 */
export const useConfirmDialog = () => {
  const [dialogState, setDialogState] = useState<ConfirmDialogState>(DEFAULT_STATE);

  const confirm = useCallback((options: {
    title?: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    confirmColor?: 'primary' | 'error' | 'warning' | 'info' | 'success';
    onConfirm: () => void;
  }) => {
    setDialogState({
      open: true,
      title: options.title || 'Confirm Action',
      message: options.message,
      confirmText: options.confirmText || 'OK',
      cancelText: options.cancelText || 'Cancel',
      confirmColor: options.confirmColor || 'primary',
      onConfirm: options.onConfirm,
    });
  }, []);

  const handleConfirm = useCallback(() => {
    dialogState.onConfirm();
    setDialogState(DEFAULT_STATE);
  }, [dialogState]);

  const handleCancel = useCallback(() => {
    setDialogState(DEFAULT_STATE);
  }, []);

  return {
    dialogState,
    confirm,
    handleConfirm,
    handleCancel,
  };
};

