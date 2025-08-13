import React from 'react';

import { DeviceDataProvider } from '../device/DeviceDataContext';
import { VNCStateProvider } from '../VNCStateContext';

import { NavigationProvider } from './NavigationContext';

interface NavigationEditorProviderProps {
  children: React.ReactNode;
}

// ========================================
// PROVIDER
// ========================================

export const NavigationEditorProvider: React.FC<NavigationEditorProviderProps> = ({ children }) => {
  return (
    <VNCStateProvider>
      <DeviceDataProvider>
        <NavigationProvider>{children}</NavigationProvider>
      </DeviceDataProvider>
    </VNCStateProvider>
  );
};

NavigationEditorProvider.displayName = 'NavigationEditorProvider';
