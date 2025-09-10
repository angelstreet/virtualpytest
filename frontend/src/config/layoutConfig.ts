/**
 * Central configuration for layout settings - unified desktop layout for all devices
 * This ensures consistent layout behavior across components
 */


// Layout configuration for StreamViewer component
export interface StreamViewerLayoutConfig {
  minHeight: string;
  aspectRatio: string;
  objectFit: 'cover' | 'contain' | 'fill';
  isMobileModel: boolean;
}

// Layout configuration for VerificationEditor component
export interface VerificationEditorLayoutConfig {
  width: number;
  height: number;
  captureHeight: number;
  objectFit: 'fill' | 'contain';
  isMobileModel: boolean;
}

/**
 * Get the unified StreamViewer layout configuration for all device types
 * Always returns desktop layout - mobile content will show with black bars
 * @param model The model name string (ignored - kept for API compatibility)
 * @returns StreamViewerLayoutConfig with unified desktop settings
 */
export const getStreamViewerLayout = (model?: string): StreamViewerLayoutConfig => {
  // Always return desktop layout for consistent UI
  return {
    minHeight: '300px',
    aspectRatio: 'auto', // Let content determine ratio, accept black bars
    objectFit: 'contain', // Always preserve aspect ratio
    isMobileModel: false, // Always false - no mobile-specific behavior
  };
};

/**
 * Get the unified VerificationEditor layout configuration for all device types
 * Always returns desktop layout for consistent verification UI
 * @param model The model name string (ignored - kept for API compatibility)
 * @returns VerificationEditorLayoutConfig with unified desktop settings
 */
export const getVerificationEditorLayout = (model?: string): VerificationEditorLayoutConfig => {
  // Always return desktop layout for consistent verification UI
  return {
    width: 640,
    height: 510,
    captureHeight: 140,
    objectFit: 'contain', // Always preserve aspect ratio
    isMobileModel: false, // Always false - no mobile-specific behavior
  };
};
