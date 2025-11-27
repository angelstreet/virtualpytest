// Export all web hooks from organized structure

// Auth Hooks
export * from './auth';

// Core Hooks
export * from './useToast';

// Controller Hooks
export * from './controller';

// Monitoring Hooks
export * from './monitoring';

// Validation Hooks
export * from './validation';

// Script Hooks
export * from './script';

// Page Hooks (domain-specific for pages)
export * from './pages/useScreenEditor';

export * from './pages/useDevice';
export * from './pages/useUserInterface';
export * from './pages/useRec';

export { useUserSession } from './useUserSession';
export { useToast } from './useToast';
export { useVerification } from './verification/useVerification';
export { useVerificationEditor } from './verification/useVerificationEditor';
export { useAction } from './actions/useAction';
export { useStreamCoordinates } from './useStreamCoordinates';

// Navigation hooks

// Component hooks
export { useHostManager } from './useHostManager';

// Page hooks
export { useRec } from './pages/useRec';
