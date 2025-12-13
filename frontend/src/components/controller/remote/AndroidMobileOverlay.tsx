import React, { useEffect, useState, useMemo } from 'react';

import { PanelInfo } from '../../../types/controller/Panel_Types';
import { AndroidElement } from '../../../types/controller/Remote_Types';
import { getZIndex } from '../../../utils/zIndexUtils';


import { buildServerUrl } from '../../../utils/buildUrlUtils';
interface ScaledElement {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
}

interface AndroidMobileOverlayProps {
  elements: AndroidElement[];
  deviceWidth: number;
  deviceHeight: number;
  isVisible: boolean;
  onElementClick?: (element: AndroidElement) => void;
  panelInfo: PanelInfo;
  host: any;
  deviceId: string;
  isLandscape: boolean; // Manual orientation toggle
}

// Element highlight colors - using centralized theme
import { ELEMENT_HIGHLIGHT_COLORS } from '../../../constants/agentChatTheme';
const COLORS = ELEMENT_HIGHLIGHT_COLORS;

export const AndroidMobileOverlay = React.memo(
  function AndroidMobileOverlay({
    elements,
    deviceWidth,
    deviceHeight,
    isVisible,
    onElementClick,
    panelInfo,
    host,
    deviceId,
    isLandscape,
  }: AndroidMobileOverlayProps) {
    const [scaledElements, setScaledElements] = useState<ScaledElement[]>([]);
    const [clickAnimation, setClickAnimation] = useState<{
      x: number;
      y: number;
      id: string;
      deviceX?: number;
      deviceY?: number;
    } | null>(null);
    const [coordinateDisplay, setCoordinateDisplay] = useState<{
      x: number;
      y: number;
      deviceX: number;
      deviceY: number;
      id: string;
    } | null>(null);

    // Simple manual orientation
    const currentOrientation = isLandscape ? 'landscape' : 'portrait';
    
    // Debug: Log orientation changes
    useEffect(() => {
      console.log(`[@AndroidMobileOverlay] Orientation changed to: ${currentOrientation}`);
    }, [currentOrientation]);

    // Add CSS animation keyframes to document head if not already present
    React.useEffect(() => {
      const styleId = 'click-animation-styles';
      if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
          @keyframes clickPulse {
            0% {
              transform: scale(0.3);
              opacity: 1;
            }
            100% {
              transform: scale(1.5);
              opacity: 0;
            }
          }
        `;
        document.head.appendChild(style);
      }
    }, []);

    const parseBounds = (bounds: { left: number; top: number; right: number; bottom: number }) => {
      // Validate input bounds
      if (
        typeof bounds.left !== 'number' ||
        typeof bounds.top !== 'number' ||
        typeof bounds.right !== 'number' ||
        typeof bounds.bottom !== 'number' ||
        isNaN(bounds.left) ||
        isNaN(bounds.top) ||
        isNaN(bounds.right) ||
        isNaN(bounds.bottom)
      ) {
        console.warn(`[@component:AndroidMobileOverlay] Invalid bounds object:`, bounds);
        return null;
      }

      const width = bounds.right - bounds.left;
      const height = bounds.bottom - bounds.top;

      return {
        x: bounds.left,
        y: bounds.top,
        width: width,
        height: height,
      };
    };

    // Calculate actual content dimensions using contain logic (preserve aspect ratio)
    const { actualContentWidth, actualContentHeight, horizontalOffset, verticalOffset } = useMemo(() => {
      if (!panelInfo || !panelInfo.deviceResolution || !panelInfo.size) {
        return { actualContentWidth: 0, actualContentHeight: 0, horizontalOffset: 0, verticalOffset: 0 };
      }

      // Use contain logic to match HLSVideoPlayer objectFit: 'contain'
      // This maintains aspect ratio and centers the content within the panel
      const deviceAspectRatio = deviceWidth / deviceHeight;
      const panelAspectRatio = panelInfo.size.width / panelInfo.size.height;

      let actualWidth, actualHeight, hOffset, vOffset;

      if (deviceAspectRatio <= panelAspectRatio) {
        // Device is narrower than panel - fit by height
        actualHeight = panelInfo.size.height;
        actualWidth = actualHeight * deviceAspectRatio;
        hOffset = (panelInfo.size.width - actualWidth) / 2;
        vOffset = 0;
      } else {
        // Device is wider than panel - fit by width
        actualWidth = panelInfo.size.width;
        actualHeight = actualWidth / deviceAspectRatio;
        hOffset = 0;
        vOffset = (panelInfo.size.height - actualHeight) / 2;
      }

      console.log('[@AndroidMobileOverlay] Contain scaling calculated:', {
        scalingMode: 'contain (preserve aspect ratio)',
        deviceAspectRatio,
        panelAspectRatio,
        deviceWidth,
        deviceHeight,
        panelWidth: panelInfo.size.width,
        panelHeight: panelInfo.size.height,
        actualWidth,
        actualHeight,
        hOffset,
        vOffset,
      });

      return {
        actualContentWidth: actualWidth,
        actualContentHeight: actualHeight,
        horizontalOffset: hOffset,
        verticalOffset: vOffset,
      };
    }, [panelInfo, deviceWidth, deviceHeight]);

    // Direct server tap function - bypasses useRemoteConfigs double conversion
    const handleDirectTap = async (deviceX: number, deviceY: number) => {
      try {
        const response = await fetch(buildServerUrl('/server/remote/tapCoordinates'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host_name: host.host_name,
            x: deviceX,
            y: deviceY,
            device_id: deviceId,
          }),
        });

        const result = await response.json();

        if (!result.success) {
          console.error(`[@component:AndroidMobileOverlay] Direct tap failed:`, result.error);
        }
      } catch (error) {
        console.error(`[@component:AndroidMobileOverlay] Direct tap error:`, error);
      }
    };

    // Calculate scaled coordinates for panel positioning
    useEffect(() => {
      if (elements.length === 0) {
        setScaledElements([]);
        return;
      }

      // Skip calculation if panelInfo is not properly defined
      if (!panelInfo || !panelInfo.deviceResolution || !panelInfo.size) {
        setScaledElements([]);
        return;
      }

      const scaled = elements
        .map((element, index) => {
          const bounds = parseBounds(element.bounds);
          if (!bounds) {
            return null;
          }

          const getElementLabel = (el: AndroidElement) => {
            // Priority: ContentDesc → Text → Class Name (same as AndroidMobileRemote)
            if (
              el.contentDesc &&
              el.contentDesc !== '<no content-desc>' &&
              el.contentDesc.trim() !== ''
            ) {
              return el.contentDesc.substring(0, 20);
            } else if (el.text && el.text !== '<no text>' && el.text.trim() !== '') {
              return `"${el.text}"`.substring(0, 20);
            } else {
              return el.className?.split('.').pop()?.substring(0, 20) || 'Unknown';
            }
          };

          // Scale elements to fit the actual content area (contain scaling)
          const scaleX = actualContentWidth / deviceWidth;
          const scaleY = actualContentHeight / deviceHeight;

          const scaledElement = {
            id: element.id,
            x: bounds.x * scaleX + horizontalOffset, // Add horizontal offset for centering
            y: bounds.y * scaleY + verticalOffset, // Add vertical offset for centering
            width: bounds.width * scaleX,
            height: bounds.height * scaleY,
            color: COLORS[index % COLORS.length],
            label: getElementLabel(element),
          };

          return scaledElement;
        })
        .filter(Boolean) as ScaledElement[];

      setScaledElements(scaled);
    }, [elements, deviceWidth, deviceHeight, panelInfo, actualContentWidth, horizontalOffset]);

    // Handle element click (higher priority)
    const handleElementClick = async (scaledElement: ScaledElement, event: React.MouseEvent) => {
      // Prevent event propagation to base layer
      event.stopPropagation();

      // Show click animation at element center
      const animationX = scaledElement.x + scaledElement.width / 2;
      const animationY = scaledElement.y + scaledElement.height / 2;
      const animationId = `element-${scaledElement.id}-${Date.now()}`;

      // Convert overlay coordinates back to device coordinates (contain scaling)
      const deviceX = Math.round(
        ((scaledElement.x - horizontalOffset) * deviceWidth) / actualContentWidth,
      );
      const deviceY = Math.round(((scaledElement.y - verticalOffset) * deviceHeight) / actualContentHeight);

      // Log coordinates
      console.log(`[@AndroidMobileOverlay] Element click - Screen: (${Math.round(animationX)}, ${Math.round(animationY)}), Device: (${deviceX}, ${deviceY})`);

      setClickAnimation({ 
        x: animationX, 
        y: animationY, 
        id: animationId,
        deviceX,
        deviceY
      });

      // Set coordinate display for 2 seconds
      const coordDisplayId = `coord-${Date.now()}`;
      setCoordinateDisplay({
        x: animationX,
        y: animationY,
        deviceX,
        deviceY,
        id: coordDisplayId
      });

      // Clear animation after 300ms
      setTimeout(() => setClickAnimation(null), 300);
      
      // Clear coordinate display after 2 seconds
      setTimeout(() => setCoordinateDisplay(null), 2000);

      const originalElement = elements.find((el) => el.id === scaledElement.id);
      if (!originalElement) return;

      // Prioritize onElementClick over direct tap for element clicks
      if (onElementClick) {
        onElementClick(originalElement);
      } else {
        await handleDirectTap(deviceX, deviceY);
      }
    };

    // Handle base layer tap (lower priority, only when not clicking on elements)
    const handleBaseTap = async (event: React.MouseEvent) => {
      // Get click coordinates relative to the content area overlay
      const rect = event.currentTarget.getBoundingClientRect();
      const contentX = event.clientX - rect.left;
      const contentY = event.clientY - rect.top;

      // Use contain scaling factors to match HLSVideoPlayer
      const scaleX = actualContentWidth / deviceWidth;
      const scaleY = actualContentHeight / deviceHeight;

      const deviceX = Math.round(contentX / scaleX);
      const deviceY = Math.round(contentY / scaleY);

      // Log coordinates
      console.log(`[@AndroidMobileOverlay] Content tap - Content: (${Math.round(contentX)}, ${Math.round(contentY)}), Device: (${deviceX}, ${deviceY})`);

      // Show click animation at tap location (use content coordinates for positioning)
      const animationId = `base-tap-${Date.now()}`;
      setClickAnimation({ 
        x: contentX, 
        y: contentY, 
        id: animationId,
        deviceX,
        deviceY
      });

      // Set coordinate display for 2 seconds
      const coordDisplayId = `coord-${Date.now()}`;
      setCoordinateDisplay({
        x: contentX,
        y: contentY,
        deviceX,
        deviceY,
        id: coordDisplayId
      });

      // Clear animation after 300ms
      setTimeout(() => setClickAnimation(null), 300);
      
      // Clear coordinate display after 2 seconds
      setTimeout(() => setCoordinateDisplay(null), 2000);

      await handleDirectTap(deviceX, deviceY);
    };

    if (!isVisible) {
      return null;
    }

    return (
      <>
        {/* Base transparent tap layer - Only covers actual content area (contain scaling) */}
        <div
          style={{
            position: 'absolute',
            left: `${panelInfo.position.x + horizontalOffset}px`,
            top: `${panelInfo.position.y + verticalOffset}px`,
            width: `${actualContentWidth}px`,
            height: `${actualContentHeight}px`,
            zIndex: getZIndex('ANDROID_MOBILE_OVERLAY'), // Base layer for tap detection
            contain: 'layout style size',
            willChange: 'transform',
            pointerEvents: 'auto', // Allow tapping on base layer
            border: '1px solid rgba(255, 208, 0, 0.18)', // Subtle border for tap area
            cursor: 'crosshair', // Crosshair cursor within actual content area
          }}
          onClick={handleBaseTap}
        ></div>

        {/* Elements layer - Higher z-index, only visible when elements exist */}
        {scaledElements.length > 0 && (
          <div
            style={{
              position: 'absolute',
              left: `${panelInfo.position.x}px`,
              top: `${panelInfo.position.y + 0}px`,
              width: `${panelInfo.size.width}px`,
              height: `${panelInfo.size.height}px`,
              zIndex: getZIndex('ANDROID_MOBILE_OVERLAY'), // Elements layer - same level as base
              contain: 'layout style size',
              willChange: 'transform',
              pointerEvents: 'none', // Allow clicks to pass through to individual elements
            }}
          >
            {/* Render scaled elements as colored rectangles */}
            {scaledElements.map((scaledElement) => (
              <div
                key={scaledElement.id}
                style={{
                  position: 'absolute',
                  left: `${scaledElement.x}px`,
                  top: `${scaledElement.y}px`,
                  width: `${scaledElement.width}px`,
                  height: `${scaledElement.height}px`,
                  backgroundColor: `${scaledElement.color}1A`, // 10% transparency (1A in hex = 26/255 ≈ 10%)
                  border: `2px solid ${scaledElement.color}`, // Colored border instead of white
                  pointerEvents: 'auto', // Allow clicks on elements (higher priority)
                  cursor: 'pointer',
                  overflow: 'hidden',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
                }}
                onClick={(event) => handleElementClick(scaledElement, event)}
                title={`${scaledElement.id}.${scaledElement.label}`}
              >
                {/* Number positioned at bottom right corner */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: '2px',
                    right: '2px',
                    fontSize: '10px',
                    color: scaledElement.color, // Colored text instead of white
                    fontWeight: 'bold',
                    lineHeight: '1',
                  }}
                >
                  {scaledElement.id}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Click animation - Highest z-index */}
        {clickAnimation && (
          <>
            {/* Click animation circle */}
            <div
              key={clickAnimation.id}
              style={{
                position: 'absolute',
                left: `${panelInfo.position.x + horizontalOffset + clickAnimation.x - 15}px`, // Use content coordinates with offset
                top: `${panelInfo.position.y + verticalOffset + clickAnimation.y - 15 + 0}px`,
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                border: '2px solid rgba(0, 123, 255, 0.8)',
                zIndex: getZIndex('ANDROID_MOBILE_OVERLAY'), // Click animation - same level
                pointerEvents: 'none',
                animation: 'clickPulse 0.3s ease-out forwards',
              }}
            />

          </>
        )}

        {/* Coordinate display - Independent 2-second display */}
        {coordinateDisplay && (
          <div
            key={coordinateDisplay.id}
            style={{
              position: 'absolute',
              left: `${panelInfo.position.x + horizontalOffset + coordinateDisplay.x + 0}px`, // Use content coordinates with offset
              top: `${panelInfo.position.y + verticalOffset + coordinateDisplay.y - 15 + 0}px`, // Use content coordinates with offset
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              color: 'white',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'monospace',
              fontWeight: 'bold',
              zIndex: getZIndex('ANDROID_MOBILE_OVERLAY'), // Same level as animation
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            {coordinateDisplay.deviceX}, {coordinateDisplay.deviceY}
          </div>
        )}
      </>
    );
  },
  (prevProps, nextProps) => {
    // Only re-render if props have actually changed
    return (
      prevProps.elements === nextProps.elements &&
      prevProps.deviceWidth === nextProps.deviceWidth &&
      prevProps.deviceHeight === nextProps.deviceHeight &&
      prevProps.isVisible === nextProps.isVisible &&
      prevProps.onElementClick === nextProps.onElementClick &&
      JSON.stringify(prevProps.panelInfo) === JSON.stringify(nextProps.panelInfo) &&
      prevProps.host === nextProps.host &&
      prevProps.deviceId === nextProps.deviceId &&
      prevProps.isLandscape === nextProps.isLandscape
    );
  },
);
