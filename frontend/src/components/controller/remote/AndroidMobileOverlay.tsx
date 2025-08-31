import React, { useEffect, useState, useMemo } from 'react';

import { PanelInfo } from '../../../types/controller/Panel_Types';
import { AndroidElement } from '../../../types/controller/Remote_Types';
import { getZIndex } from '../../../utils/zIndexUtils';
import { getDeviceOrientation } from '../../../utils/userinterface/resolutionUtils';

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
  panelInfo: PanelInfo; // Made required - no fallback to screenshot
  host: any; // Add host for direct server calls
  deviceId: string; // Add deviceId for API calls
}

// Same colors as the original UIElementsOverlay
const COLORS = ['#FF0000', '#0066FF', '#FFD700', '#00CC00', '#9900FF'];

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

    // Detect device orientation
    const currentOrientation = useMemo(() => {
      return getDeviceOrientation(deviceWidth, deviceHeight);
    }, [deviceWidth, deviceHeight]);

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

    // Calculate actual content dimensions and offsets (orientation-aware)
    const { actualContentWidth, actualContentHeight, horizontalOffset, verticalOffset } = React.useMemo(() => {
      if (!panelInfo || !panelInfo.deviceResolution || !panelInfo.size) {
        return { actualContentWidth: 0, actualContentHeight: 0, horizontalOffset: 0, verticalOffset: 0 };
      }

      const deviceAspectRatio = deviceWidth / deviceHeight;
      const panelAspectRatio = panelInfo.size.width / panelInfo.size.height;

      let actualWidth, actualHeight, hOffset, vOffset;

      if (currentOrientation === 'portrait') {
        // Portrait: Height is reference, calculate width
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
      } else {
        // Landscape: Width is reference, calculate height
        if (deviceAspectRatio >= panelAspectRatio) {
          // Device is wider than panel - fit by width
          actualWidth = panelInfo.size.width;
          actualHeight = actualWidth / deviceAspectRatio;
          hOffset = 0;
          vOffset = (panelInfo.size.height - actualHeight) / 2;
        } else {
          // Device is narrower than panel - fit by height
          actualHeight = panelInfo.size.height;
          actualWidth = actualHeight * deviceAspectRatio;
          hOffset = (panelInfo.size.width - actualWidth) / 2;
          vOffset = 0;
        }
      }

      console.log('[@AndroidMobileOverlay] Orientation-aware content calculated:', {
        orientation: currentOrientation,
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
    }, [panelInfo, deviceWidth, deviceHeight, currentOrientation]);

    // Direct server tap function - bypasses useRemoteConfigs double conversion
    const handleDirectTap = async (deviceX: number, deviceY: number) => {
      try {
        const response = await fetch('/server/remote/tapCoordinates', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host: host,
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

          // Scale elements to fit the actual stream content size (not panel size)
          const scaleX = actualContentWidth / deviceWidth;
          const scaleY = panelInfo.size.height / deviceHeight;

          const scaledElement = {
            id: element.id,
            x: bounds.x * scaleX + horizontalOffset, // Add offset to center horizontally
            y: bounds.y * scaleY, // No vertical offset needed
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

      // Convert overlay coordinates back to device coordinates
      const deviceX = Math.round(
        ((scaledElement.x - horizontalOffset) * deviceWidth) / actualContentWidth,
      );
      const deviceY = Math.round((scaledElement.y * deviceHeight) / panelInfo.size.height);

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
      // Get click coordinates relative to the viewport (fullscreen overlay)
      const viewportX = event.clientX;
      const viewportY = event.clientY;

      // Convert viewport coordinates to panel coordinates
      const panelX = viewportX - panelInfo.position.x;
      const panelY = viewportY - panelInfo.position.y;

      // Check if click is within panel bounds
      if (panelX < 0 || panelX > panelInfo.size.width || panelY < 0 || panelY > panelInfo.size.height) {
        console.log(`[@AndroidMobileOverlay] Click outside panel bounds, ignoring`);
        return;
      }

      // Convert panel coordinates to content coordinates (accounting for offsets)
      const contentX = panelX - horizontalOffset;
      const contentY = panelY - verticalOffset;

      // Check if click is within content area
      if (contentX < 0 || contentX > actualContentWidth || contentY < 0 || contentY > actualContentHeight) {
        console.log(`[@AndroidMobileOverlay] Click outside content area, ignoring`);
        return;
      }

      // Use orientation-aware scaling factors
      const scaleX = actualContentWidth / deviceWidth;
      const scaleY = actualContentHeight / deviceHeight;

      const deviceX = Math.round(contentX / scaleX);
      const deviceY = Math.round(contentY / scaleY);

      // Log coordinates
      console.log(`[@AndroidMobileOverlay] Fullscreen tap - Viewport: (${Math.round(viewportX)}, ${Math.round(viewportY)}), Panel: (${Math.round(panelX)}, ${Math.round(panelY)}), Content: (${Math.round(contentX)}, ${Math.round(contentY)}), Device: (${deviceX}, ${deviceY})`);

      // Show click animation at tap location (use panel coordinates for positioning)
      const animationId = `base-tap-${Date.now()}`;
      setClickAnimation({ 
        x: panelX, 
        y: panelY, 
        id: animationId,
        deviceX,
        deviceY
      });

      // Set coordinate display for 2 seconds
      const coordDisplayId = `coord-${Date.now()}`;
      setCoordinateDisplay({
        x: panelX,
        y: panelY,
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
        {/* Base transparent tap layer - Covers full screen for landscape tapping */}
        <div
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            width: '100vw',
            height: '100vh',
            zIndex: getZIndex('ANDROID_MOBILE_OVERLAY'), // Base layer for tap detection
            contain: 'layout style size',
            willChange: 'transform',
            pointerEvents: 'auto', // Allow tapping on base layer
            cursor: 'default', // Default cursor for fullscreen area
          }}
          onClick={handleBaseTap}
        >
          {/* Visual content area indicator - shows actual device content area */}
          <div
            style={{
              position: 'absolute',
              left: `${panelInfo.position.x + horizontalOffset}px`,
              top: `${panelInfo.position.y + verticalOffset}px`,
              width: `${actualContentWidth}px`,
              height: `${actualContentHeight}px`,
              border: '1px solid rgba(0, 255, 0, 0.3)',
              pointerEvents: 'none',
              boxSizing: 'border-box',
            }}
          />
          
          {/* Cursor area - crosshair only within content bounds */}
          <div
            style={{
              position: 'absolute',
              left: `${panelInfo.position.x + horizontalOffset}px`,
              top: `${panelInfo.position.y + verticalOffset}px`,
              width: `${actualContentWidth}px`,
              height: `${actualContentHeight}px`,
              cursor: 'crosshair',
              pointerEvents: 'none', // Don't interfere with clicks, just show cursor
              zIndex: 1,
            }}
          />
        </div>

        {/* Elements layer - Higher z-index, only visible when elements exist */}
        {scaledElements.length > 0 && (
          <div
            style={{
              position: 'fixed',
              left: `${panelInfo.position.x}px`,
              top: `${panelInfo.position.y}px`,
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
                position: 'fixed',
                left: `${panelInfo.position.x + clickAnimation.x - 15}px`, // Use panel coordinates directly
                top: `${panelInfo.position.y + clickAnimation.y - 15}px`,
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
              position: 'fixed',
              left: `${panelInfo.position.x + coordinateDisplay.x + 20}px`, // Use panel coordinates directly
              top: `${panelInfo.position.y + coordinateDisplay.y - 15}px`, // Use panel coordinates directly
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
      prevProps.deviceId === nextProps.deviceId
    );
  },
);
