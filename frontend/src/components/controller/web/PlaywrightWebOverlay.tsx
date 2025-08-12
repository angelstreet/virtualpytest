import React, { useEffect, useState } from 'react';

import { PanelInfo } from '../../../types/controller/Panel_Types';
import { WebElement } from '../../../types/controller/Web_Types';
import { Host } from '../../../types/common/Host_Types';
import { getZIndex } from '../../../utils/zIndexUtils';
import '../../../styles/webOverlayAnimations.css';

interface ScaledElement {
  selector: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
  index: number;
}

interface PlaywrightWebOverlayProps {
  elements: WebElement[];
  isVisible: boolean;
  onElementClick?: (element: WebElement) => void;
  panelInfo: PanelInfo;
  host: Host;
}

// Same colors as Android mobile overlay for consistency
const COLORS = ['#FF0000', '#0066FF', '#FFD700', '#00CC00', '#9900FF'];

export const PlaywrightWebOverlay = React.memo(
  function PlaywrightWebOverlay({
    elements,
    isVisible,
    onElementClick,
    panelInfo,
    host,
  }: PlaywrightWebOverlayProps) {
    const [scaledElements, setScaledElements] = useState<ScaledElement[]>([]);
    const [clickAnimation, setClickAnimation] = useState<{
      x: number;
      y: number;
      id: string;
    } | null>(null);
    const [coordinateDisplay, setCoordinateDisplay] = useState<{
      x: number;
      y: number;
      id: string;
    } | null>(null);

    // Calculate scaled elements for overlay positioning
    useEffect(() => {
      if (elements.length === 0) {
        setScaledElements([]);
        return;
      }

      const scaled = elements
        .map((element, index) => {
          const getElementLabel = (el: WebElement) => {
            // Priority: aria-label → textContent → tagName + id
            if (el.attributes['aria-label']) {
              return el.attributes['aria-label'].substring(0, 20);
            } else if (el.textContent && el.textContent.trim()) {
              return `"${el.textContent.trim()}"`.substring(0, 20);
            } else {
              return `${el.tagName}${el.id ? '#' + el.id : ''}`.substring(0, 20);
            }
          };

          const scaledElement = {
            selector: element.selector,
            x: element.position.x,
            y: element.position.y,
            width: element.position.width,
            height: element.position.height,
            color: COLORS[index % COLORS.length],
            label: getElementLabel(element),
            index: element.index,
          };

          return scaledElement;
        })
        .filter(Boolean) as ScaledElement[];

      setScaledElements(scaled);
    }, [elements]);

    // Handle element click
    const handleElementClick = async (scaledElement: ScaledElement, event: React.MouseEvent) => {
      event.stopPropagation();

      // Show click animation at element center
      const animationX = scaledElement.x + scaledElement.width / 2;
      const animationY = scaledElement.y + scaledElement.height / 2;
      const animationId = `element-${scaledElement.index}-${Date.now()}`;

      console.log(`[PlaywrightWebOverlay] Element click - Position: (${Math.round(animationX)}, ${Math.round(animationY)}), Selector: ${scaledElement.selector}`);

      setClickAnimation({ 
        x: animationX, 
        y: animationY, 
        id: animationId
      });

      // Set coordinate display for 2 seconds
      const coordDisplayId = `coord-${Date.now()}`;
      setCoordinateDisplay({
        x: animationX,
        y: animationY,
        id: coordDisplayId
      });

      // Clear animation after 300ms
      setTimeout(() => setClickAnimation(null), 300);
      
      // Clear coordinate display after 2 seconds
      setTimeout(() => setCoordinateDisplay(null), 2000);

      const originalElement = elements.find((el) => el.selector === scaledElement.selector);
      if (originalElement && onElementClick) {
        onElementClick(originalElement);
      }
    };

    // Handle base layer tap
    const handleBaseTap = async (event: React.MouseEvent) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const contentX = event.clientX - rect.left;
      const contentY = event.clientY - rect.top;

      console.log(`[PlaywrightWebOverlay] Base tap - Position: (${Math.round(contentX)}, ${Math.round(contentY)})`);

      // Show click animation at tap location
      const animationId = `base-tap-${Date.now()}`;
      setClickAnimation({ 
        x: contentX, 
        y: contentY, 
        id: animationId
      });

      // Set coordinate display for 2 seconds
      const coordDisplayId = `coord-${Date.now()}`;
      setCoordinateDisplay({
        x: contentX,
        y: contentY,
        id: coordDisplayId
      });

      // Clear animation after 300ms
      setTimeout(() => setClickAnimation(null), 300);
      
      // Clear coordinate display after 2 seconds
      setTimeout(() => setCoordinateDisplay(null), 2000);
    };

    if (!isVisible) {
      return null;
    }

    return (
      <>
        {/* Base transparent tap layer - Full viewport */}
        <div
          style={{
            position: 'fixed',
            left: `${panelInfo.position.x}px`,
            top: `${panelInfo.position.y}px`,
            width: `${panelInfo.size.width}px`,
            height: `${panelInfo.size.height}px`,
            zIndex: getZIndex('DEBUG_OVERLAY'), // Use web overlay z-index
            contain: 'layout style size',
            willChange: 'transform',
            pointerEvents: 'auto',
            border: '1px solid rgba(255, 0, 0, 0.3)', // Red border for web overlay
            cursor: 'crosshair',
          }}
          onClick={handleBaseTap}
        ></div>

        {/* Elements layer */}
        {scaledElements.length > 0 && (
          <div
            style={{
              position: 'fixed',
              left: `${panelInfo.position.x}px`,
              top: `${panelInfo.position.y}px`,
              width: `${panelInfo.size.width}px`,
              height: `${panelInfo.size.height}px`,
              zIndex: getZIndex('DEBUG_OVERLAY'),
              contain: 'layout style size',
              willChange: 'transform',
              pointerEvents: 'none',
            }}
          >
            {/* Render scaled elements as colored rectangles */}
            {scaledElements.map((scaledElement) => (
              <div
                key={scaledElement.selector}
                style={{
                  position: 'absolute',
                  left: `${scaledElement.x}px`,
                  top: `${scaledElement.y}px`,
                  width: `${scaledElement.width}px`,
                  height: `${scaledElement.height}px`,
                  backgroundColor: `${scaledElement.color}1A`, // 10% transparency
                  border: `2px solid ${scaledElement.color}`,
                  pointerEvents: 'auto',
                  cursor: 'pointer',
                  overflow: 'hidden',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
                }}
                onClick={(event) => handleElementClick(scaledElement, event)}
                title={`${scaledElement.index}.${scaledElement.label} - ${scaledElement.selector}`}
              >
                {/* Element index in corner */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: '2px',
                    right: '2px',
                    fontSize: '10px',
                    color: scaledElement.color,
                    fontWeight: 'bold',
                    lineHeight: '1',
                  }}
                >
                  {scaledElement.index}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Click animation */}
        {clickAnimation && (
          <div
            key={clickAnimation.id}
            style={{
              position: 'fixed',
              left: `${panelInfo.position.x + clickAnimation.x - 15}px`,
              top: `${panelInfo.position.y + clickAnimation.y - 15}px`,
              width: '30px',
              height: '30px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              border: '2px solid rgba(255, 0, 0, 0.8)',
              zIndex: getZIndex('DEBUG_OVERLAY'),
              pointerEvents: 'none',
              animation: 'webClickPulse 0.3s ease-out forwards',
            }}
          />
        )}

        {/* Coordinate display */}
        {coordinateDisplay && (
          <div
            key={coordinateDisplay.id}
            style={{
              position: 'fixed',
              left: `${panelInfo.position.x + coordinateDisplay.x + 20}px`,
              top: `${panelInfo.position.y + coordinateDisplay.y - 15}px`,
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              color: 'white',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'monospace',
              fontWeight: 'bold',
              zIndex: getZIndex('DEBUG_OVERLAY'),
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            {Math.round(coordinateDisplay.x)}, {Math.round(coordinateDisplay.y)}
          </div>
        )}
      </>
    );
  },
  (prevProps, nextProps) => {
    return (
      prevProps.elements === nextProps.elements &&
      prevProps.isVisible === nextProps.isVisible &&
      prevProps.onElementClick === nextProps.onElementClick &&
      JSON.stringify(prevProps.panelInfo) === JSON.stringify(nextProps.panelInfo) &&
      prevProps.host === nextProps.host
    );
  },
);
