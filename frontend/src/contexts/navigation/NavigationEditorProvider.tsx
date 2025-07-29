import React from 'react';

import { DeviceDataProvider } from '../device/DeviceDataContext';

import { NavigationProvider } from './NavigationContext';
import { NavigationConfigProvider } from './NavigationConfigContext';

interface NavigationEditorProviderProps {
  children: React.ReactNode;
}

// ========================================
// PROVIDER
// ========================================

export const NavigationEditorProvider: React.FC<NavigationEditorProviderProps> = ({ children }) => {
  return (
    <DeviceDataProvider>
      <NavigationConfigProvider>
        <NavigationProvider>{children}</NavigationProvider>
      </NavigationConfigProvider>
    </DeviceDataProvider>
  );
};

NavigationEditorProvider.displayName = 'NavigationEditorProvider';
