/**
 * Simple Z-Index Management - Order Based
 *
 * Components are listed in order from bottom to top.
 * Each component gets a z-index based on its position in the list.
 */

// Z-index order from bottom to top
// Each position gets 10 z-index points (index + 1) * 10
const Z_INDEX_ORDER = [
  // Base content layers
  'CONTENT', // 10 - Base content, images, videos
  'NAVIGATION_NODES', // 20 - Navigation nodes and their handles
  'NAVIGATION_NODE_HANDLES', // 30 - Node connection handles (slight overlap)
  'NAVIGATION_NODE_BADGES', // 40 - Node badges (verification, subtree)
  'NAVIGATION_NODE_CURRENT_POSITION', // 50 - Current position indicators
  
  // UI elements and panels (background)
  'UI_ELEMENTS', // 60 - General UI elements
  'DESKTOP_CONTROL_PANEL', // 70 - Desktop Control Panel (behind navigation panels)
  'REMOTE_PANELS', // 80 - Remote control panels
  'VIDEO_CAPTURE_CONTROLS', // 90 - Video capture playback controls
  'VIDEO_CAPTURE_OVERLAY', // 100 - Video capture drag selection
  
  // Streaming and visualization layers (same level as control panels)
  'STREAM_VIEWER', // 110 - Stream viewers
  'HDMI_STREAM', // 120 - HDMI stream displays
  'VNC_STREAM', // 130 - VNC stream displays
  'VERIFICATION_EDITOR', // 140 - Verification editors
  
  // Navigation panels (middle layer - above streams and desktop panels)
  'NAVIGATION_PANELS', // 150 - General navigation panels
  'NAVIGATION_EDGE_PANEL', // 160 - Edge editing panel
  'NAVIGATION_SELECTION_PANEL', // 170 - Node selection panel
  'NAVIGATION_GOTO_PANEL', // 180 - Navigation goto panel
  'NAVIGATION_CONFIRMATION', // 190 - Navigation confirmation dialogs
  'NAVIGATION_DIALOGS', // 200 - Navigation dialogs (create/edit)
  
  // Top-level UI
  'TOOLTIPS', // 210 - Tooltips and hints
  'READ_ONLY_INDICATOR', // 220 - Read-only mode indicators
  'HEADER', // 230 - Page headers
  'HEADER_DROPDOWN', // 240 - Header dropdown menus
  
  // Modals and screenshots (high layer)
  'MODAL_BACKDROP', // 250 - Modal backdrop/overlay
  'MODAL_CONTENT', // 260 - Modal content windows
  'SCREENSHOT_MODAL', // 270 - Screenshot viewing modals
  
  // Interactive overlays (highest layer - on top of everything)
  'APPIUM_OVERLAY', // 280 - Appium element overlays
  'ANDROID_MOBILE_OVERLAY', // 290 - Android mobile overlays
  'DEBUG_OVERLAY', // 300 - Debug information overlays
  'SCREENSHOT_CAPTURE_OVERLAY', // 310 - Screenshot capture drag selection overlay (above all overlays)
] as const;

type ZIndexComponent = (typeof Z_INDEX_ORDER)[number];

/**
 * Get z-index for a component based on its order
 * Each position gets 10 z-index points to allow for micro-adjustments
 */
export const getZIndex = (component: ZIndexComponent, offset: number = 0): number => {
  const index = Z_INDEX_ORDER.indexOf(component);
  if (index === -1) {
    console.warn(`Unknown z-index component: ${component}`);
    return 1;
  }
  return (index + 1) * 10 + offset;
};

/**
 * Get z-index style object for React components
 */
export const getZIndexStyle = (component: ZIndexComponent, offset: number = 0) => ({
  zIndex: getZIndex(component, offset),
});

/**
 * Get all z-index values (for debugging)
 */
export const getAllZIndexes = (): Record<ZIndexComponent, number> => {
  const result = {} as Record<ZIndexComponent, number>;
  Z_INDEX_ORDER.forEach((component) => {
    result[component] = getZIndex(component);
  });
  return result;
};

// Export the type for TypeScript
export type { ZIndexComponent };