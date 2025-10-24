import React from 'react';

import { DeviceDataProvider } from '../device/DeviceDataContext';
import { VNCStateProvider } from '../VNCStateContext';

import { NavigationProvider } from './NavigationContext';
import { NavigationPreviewCacheProvider } from './NavigationPreviewCacheContext';

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
        <NavigationPreviewCacheProvider>
          <NavigationProvider>{children}</NavigationProvider>
        </NavigationPreviewCacheProvider>
      </DeviceDataProvider>
    </VNCStateProvider>
  );
};

NavigationEditorProvider.displayName = 'NavigationEditorProvider';
