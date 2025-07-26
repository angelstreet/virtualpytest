import {
  OpenInFull,
  CloseFullscreen,
  KeyboardArrowDown,
  KeyboardArrowUp,
} from '@mui/icons-material';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import React, { useState, useEffect, useMemo } from 'react';

import { getConfigurableRemotePanelLayout, loadRemoteConfig } from '../../../config/remote';
import { Host } from '../../../types/common/Host_Types';

import { PlaywrightWebTerminal } from './PlaywrightWebTerminal';

interface WebPanelProps {
  host: Host;
  deviceId: string; // Device ID to select the correct device and controllers
  deviceModel: string; // Device model for web config loading
  isConnected?: boolean; // Connection status from parent
  onReleaseControl?: () => void;
  initialCollapsed?: boolean;
  // NEW: Stream container dimensions for modal context
  streamContainerDimensions?: {
    width: number;
    height: number;
    x: number;
    y: number;
  };
}

export const WebPanel = React.memo(
  function WebPanel({
    host,
    deviceId,
    deviceModel,
    isConnected,
    onReleaseControl,
    initialCollapsed = true,
    streamContainerDimensions,
  }: WebPanelProps) {
    console.log(`[@component:WebPanel] Props debug:`, {
      deviceId,
      deviceModel,
      initialCollapsed,
    });

    // Panel state - three states: expanded, collapsed, minimized
    const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);
    const [isMinimized, setIsMinimized] = useState(false);
    const [webConfig, setWebConfig] = useState<any>(null);

    // Load web config for the device type
    useEffect(() => {
      const loadConfig = async () => {
        const config = await loadRemoteConfig(deviceModel);
        setWebConfig(config);
      };

      loadConfig();
    }, [deviceModel]);

    // Get configurable layout from device config - memoized to prevent infinite loops
    const panelLayout = useMemo(() => {
      return getConfigurableRemotePanelLayout(deviceModel, webConfig);
    }, [deviceModel, webConfig]);

    // Calculate dimensions inline - no state, no useEffects
    const collapsedWidth = panelLayout.collapsed.width;
    const collapsedHeight = panelLayout.collapsed.height;
    const expandedWidth = panelLayout.expanded.width;
    const expandedHeight = panelLayout.expanded.height;
    const headerHeight = webConfig?.panel_layout?.header?.height || '48px';

    // Current panel dimensions based on state
    const currentWidth = isCollapsed ? collapsedWidth : expandedWidth;
    const currentHeight = isMinimized
      ? headerHeight
      : isCollapsed
        ? collapsedHeight
        : expandedHeight;

    console.log(`[@component:WebPanel] Panel state debug:`, {
      isCollapsed,
      isMinimized,
      currentWidth,
      currentHeight,
    });

    // Smart toggle handlers with minimized state logic
    const handleMinimizeToggle = () => {
      if (isMinimized) {
        // Restore from minimized to collapsed state
        setIsMinimized(false);
        setIsCollapsed(true);
        console.log(
          `[@component:WebPanel] Restored from minimized to collapsed for ${deviceModel}`,
        );
      } else {
        // Minimize the panel
        setIsMinimized(true);
        console.log(`[@component:WebPanel] Minimized panel for ${deviceModel}`);
      }
    };

    const handleExpandCollapseToggle = () => {
      if (isMinimized) {
        // First restore from minimized to collapsed, then user can click again to expand
        setIsMinimized(false);
        setIsCollapsed(true);
        console.log(
          `[@component:WebPanel] Restored from minimized to collapsed for ${deviceModel}`,
        );
      } else {
        // Normal expand/collapse logic
        setIsCollapsed(!isCollapsed);
        console.log(
          `[@component:WebPanel] Toggling panel state to ${!isCollapsed ? 'collapsed' : 'expanded'} for ${deviceModel}`,
        );
      }
    };

    // Build position styles - detect modal context
    const positionStyles: any = streamContainerDimensions
      ? {
          // Modal context: use relative positioning within the modal container
          position: 'relative',
          width: '100%',
          height: '100%',
        }
      : {
          // Floating panel context: use fixed positioning
          position: 'fixed',
          zIndex: panelLayout.zIndex,
          // Always anchor at bottom-right (collapsed position)
          bottom: panelLayout.collapsed.position.bottom || '20px',
          right: panelLayout.collapsed.position.right || '20px',
        };

    // Create stable reference for streamContainerDimensions to prevent unnecessary re-renders
    const stableStreamContainerDimensions = useMemo(() => {
      return streamContainerDimensions;
    }, [streamContainerDimensions]);

    const renderWebComponent = useMemo(() => {
      switch (deviceModel) {
        case 'host_vnc':
          // Playwright Web Terminal for host_vnc devices with web capability
          return <PlaywrightWebTerminal host={host} />;
        case 'host_web':
          // Legacy case - redirect to host_vnc behavior
          return <PlaywrightWebTerminal host={host} />;
        default:
          return (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                p: 2,
              }}
            >
              <Typography variant="body2" color="textSecondary" textAlign="center">
                Unsupported web device: {deviceModel}
                <br />
                Use 'host_vnc' with web capability instead
              </Typography>
            </Box>
          );
      }
    }, [
      host,
      deviceId,
      deviceModel,
      onReleaseControl,
      isCollapsed,
      currentWidth,
      currentHeight,
      stableStreamContainerDimensions,
    ]);

    return (
      <Box sx={positionStyles}>
        {/* Inner content container - uses appropriate size for state */}
        <Box
          sx={{
            width: streamContainerDimensions ? '100%' : currentWidth,
            height: streamContainerDimensions ? '100%' : currentHeight,
            position: streamContainerDimensions ? 'relative' : 'absolute',
            // Simple positioning - bottom and right anchored (only for floating panels)
            ...(streamContainerDimensions
              ? {}
              : {
                  bottom: 0,
                  right: 0,
                }),
            backgroundColor: 'background.paper',
            border: streamContainerDimensions ? 'none' : '1px solid',
            borderColor: 'divider',
            borderRadius: streamContainerDimensions ? 0 : 1,
            boxShadow: streamContainerDimensions ? 'none' : 3,
            overflow: 'hidden',
            transition: streamContainerDimensions
              ? 'none'
              : 'width 0.3s ease-in-out, height 0.3s ease-in-out',
          }}
        >
          {/* Header with minimize and expand/collapse buttons */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              p: parseInt(webConfig?.panel_layout?.header?.padding || '8px') / 8,
              height: headerHeight,
              borderBottom: isMinimized
                ? 'none'
                : `1px solid ${webConfig?.panel_layout?.header?.borderColor || '#333'}`,
              bgcolor: webConfig?.panel_layout?.header?.backgroundColor || '#1E1E1E',
              color: webConfig?.panel_layout?.header?.textColor || '#ffffff',
            }}
          >
            {/* Center: Title */}
            <Typography
              variant="subtitle2"
              sx={{
                fontSize: webConfig?.panel_layout?.header?.fontSize || '0.875rem',
                fontWeight: webConfig?.panel_layout?.header?.fontWeight || 'bold',
                flex: 1,
                textAlign: 'center',
              }}
            >
              {webConfig?.remote_info?.name || `${deviceModel} Web`}
            </Typography>

            {/* Right side: Minimize and Expand/Collapse buttons */}
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {/* Minimize/Restore button */}
              <Tooltip title={isMinimized ? 'Restore Panel' : 'Minimize Panel'}>
                <IconButton
                  size={webConfig?.panel_layout?.header?.iconSize || 'small'}
                  onClick={handleMinimizeToggle}
                  sx={{ color: 'inherit' }}
                >
                  {isMinimized ? (
                    <KeyboardArrowUp
                      fontSize={webConfig?.panel_layout?.header?.iconSize || 'small'}
                    />
                  ) : (
                    <KeyboardArrowDown
                      fontSize={webConfig?.panel_layout?.header?.iconSize || 'small'}
                    />
                  )}
                </IconButton>
              </Tooltip>

              {/* Expand/Collapse button */}
              <Tooltip
                title={
                  isMinimized ? 'Restore Panel' : isCollapsed ? 'Expand Panel' : 'Collapse Panel'
                }
              >
                <IconButton
                  size={webConfig?.panel_layout?.header?.iconSize || 'small'}
                  onClick={handleExpandCollapseToggle}
                  sx={{ color: 'inherit' }}
                >
                  {isCollapsed ? (
                    <OpenInFull fontSize={webConfig?.panel_layout?.header?.iconSize || 'small'} />
                  ) : (
                    <CloseFullscreen
                      fontSize={webConfig?.panel_layout?.header?.iconSize || 'small'}
                    />
                  )}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Web Content - hidden when minimized */}
          {!isMinimized && (
            <Box
              sx={{
                height: `calc(100% - ${headerHeight})`,
                overflow: 'hidden',
              }}
            >
              {renderWebComponent}
            </Box>
          )}
        </Box>
      </Box>
    );
  },
  (prevProps, nextProps) => {
    // Custom comparison function to prevent unnecessary re-renders
    // Only re-render if meaningful props have changed
    const hostChanged = JSON.stringify(prevProps.host) !== JSON.stringify(nextProps.host);
    const deviceIdChanged = prevProps.deviceId !== nextProps.deviceId;
    const deviceModelChanged = prevProps.deviceModel !== nextProps.deviceModel;
    const initialCollapsedChanged = prevProps.initialCollapsed !== nextProps.initialCollapsed;
    const onReleaseControlChanged = prevProps.onReleaseControl !== nextProps.onReleaseControl;
    const streamContainerDimensionsChanged =
      JSON.stringify(prevProps.streamContainerDimensions) !==
      JSON.stringify(nextProps.streamContainerDimensions);

    // Return true if props are equal (don't re-render), false if they changed (re-render)
    const shouldSkipRender =
      !hostChanged &&
      !deviceIdChanged &&
      !deviceModelChanged &&
      !initialCollapsedChanged &&
      !onReleaseControlChanged &&
      !streamContainerDimensionsChanged;

    if (!shouldSkipRender) {
      console.log(`[@component:WebPanel] Re-rendering due to prop changes:`, {
        hostChanged,
        deviceIdChanged,
        deviceModelChanged,
        initialCollapsedChanged,
        onReleaseControlChanged,
        streamContainerDimensionsChanged,
      });
    }

    return shouldSkipRender;
  },
);
