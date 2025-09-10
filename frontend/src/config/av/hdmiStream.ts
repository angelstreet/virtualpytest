// Shared constants for HDMI Stream configuration
export const HDMI_STREAM_HEADER_HEIGHT = '40px';

import { DEFAULT_DEVICE_RESOLUTION } from '../deviceResolutions';

export const hdmiStreamConfig = {
  stream_info: {
    name: 'HDMI',
    type: 'hdmi_stream' as const,
    default_quality: 'high' as const,
    supported_resolutions: [`${DEFAULT_DEVICE_RESOLUTION.width}x${DEFAULT_DEVICE_RESOLUTION.height}`, '1280x720', '640x480'] as const,
    default_resolution: `${DEFAULT_DEVICE_RESOLUTION.width}x${DEFAULT_DEVICE_RESOLUTION.height}` as const,
  },
  panel_layout: {
    collapsed: {
      width: '300px',
      height: '200px',
      position: {
        bottom: '20px',
        left: '20px',
      },
    },
    expanded: {
      width: '700px',
      height: '500px',
      position: {
        bottom: '20px',
        right: '20px',
      },
    },
    showControlsInCollapsed: false,
    showControlsInExpanded: true,
    header: {
      height: HDMI_STREAM_HEADER_HEIGHT,
      fontSize: '0.875rem',
      fontWeight: 'bold',
      iconSize: 'small',
      padding: '8px',
      backgroundColor: '#1E1E1E',
      borderColor: '#333',
      textColor: '#ffffff',
    },
  },
  content_layout: {
    collapsed: {
      objectFit: 'contain' as const,
      width: '100%',
      height: 'auto',
    },
    expanded: {
      objectFit: 'contain' as const,
      width: '100%',
      height: 'auto',
    },
  },
} as const;

// Mobile config removed - all devices use unified desktop layout

export type HdmiStreamConfig = typeof hdmiStreamConfig;

/**
 * Get unified stream content layout configuration for all device types
 * Always returns desktop layout - mobile content will show with black bars
 * @param deviceModel The device model (ignored - kept for API compatibility)
 * @param isExpanded Whether the panel is in expanded state
 * @returns Content layout configuration for the stream
 */
export const getStreamContentLayout = (_deviceModel?: string, isExpanded: boolean = false) => {
  // Always use desktop config for consistent layout
  return isExpanded ? hdmiStreamConfig.content_layout.expanded : hdmiStreamConfig.content_layout.collapsed;
}; 