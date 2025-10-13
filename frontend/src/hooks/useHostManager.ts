import { useContext } from 'react';

import { HostManagerContext, HostManagerContextType } from '../contexts/HostManagerContext';
import { HostDataContext, HostDataContextType } from '../contexts/HostDataContext';
import { HostControlContext, HostControlContextType } from '../contexts/HostControlContext';

/**
 * Hook to access static host data (rarely changes)
 * Use this hook when you only need to read host/device data without subscribing to control state changes.
 * This prevents unnecessary re-renders when device control state changes.
 */
export const useHostData = (): HostDataContextType => {
  const context = useContext(HostDataContext);
  if (!context) {
    throw new Error('useHostData must be used within a HostManagerProvider');
  }
  return context;
};

/**
 * Hook to access device control state (changes frequently)
 * Use this hook when you need to interact with device control state or actions.
 * Components using this hook will re-render when control state changes.
 */
export const useHostControl = (): HostControlContextType => {
  const context = useContext(HostControlContext);
  if (!context) {
    throw new Error('useHostControl must be used within a HostManagerProvider');
  }
  return context;
};

/**
 * Legacy hook to access the combined HostManager context
 * Use this for backward compatibility. New code should use useHostData() or useHostControl() instead.
 * @deprecated Use useHostData() for static data or useHostControl() for control state
 */
export const useHostManager = (): HostManagerContextType => {
  const context = useContext(HostManagerContext);
  if (!context) {
    throw new Error('useHostManager must be used within a HostManagerProvider');
  }
  return context;
};
