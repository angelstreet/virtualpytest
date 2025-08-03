import React, { useState, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';

import { NODE_TYPE_COLORS, UI_BADGE_COLORS } from '../../config/validationColors';
import { useNavigation } from '../../contexts/navigation/NavigationContext';

import { useValidationColors } from '../../hooks/validation/useValidationColors';
import type { UINavigationNode as UINavigationNodeType, UINavigationEdge } from '../../types/pages/Navigation_Types';

export const UIActionNode: React.FC<NodeProps<UINavigationNodeType['data']>> = ({
  data,
  selected: _selected,
  id,
}) => {
  const { currentNodeId } = useNavigation();

  const [isScreenshotModalOpen, setIsScreenshotModalOpen] = useState(false);
  const [imageKey, setImageKey] = useState<string | number>(0); // Key to force image refresh
  const { getEdges } = useReactFlow();
  const currentEdges = getEdges();
  const { getNodeColors } = useValidationColors(currentEdges as UINavigationEdge[]);

  // Use screenshot URL with aggressive cache-busting
  const screenshotUrl = React.useMemo(() => {
    if (!data.screenshot) return null;

    // Use multiple cache-busting parameters to ensure fresh load
    const baseUrl = data.screenshot.split('?')[0]; // Remove existing params
    const timestamp = data.screenshot_timestamp || Date.now();
    const randomKey = imageKey || Math.random().toString(36).substr(2, 9);

    return `${baseUrl}?v=${timestamp}&key=${randomKey}&cb=${Date.now()}`;
  }, [data.screenshot, data.screenshot_timestamp, imageKey]);

  // Listen for screenshot update events and force immediate refresh
  useEffect(() => {
    const handleScreenshotUpdate = (event: CustomEvent) => {
      if (event.detail.nodeId === id) {
        console.log(
          `[@component:UIActionNode] Screenshot updated for node ${id}, forcing refresh`,
        );

        // Use cache-buster from event for immediate refresh
        if (event.detail.cacheBuster) {
          setImageKey(event.detail.cacheBuster);
        } else {
          setImageKey(Date.now().toString() + Math.random().toString(36).substr(2, 9));
        }
      }
    };

    // TypeScript-compatible event listener
    const listener = handleScreenshotUpdate as EventListener;
    window.addEventListener('screenshotUpdated', listener);

    return () => {
      window.removeEventListener('screenshotUpdated', listener);
    };
  }, [id]);

  // Check if this is the current position
  const isCurrentPosition = currentNodeId === id;

  // Get dynamic colors based on validation status
  const nodeColors = getNodeColors(data.type);

  // Action node colors from validationColors
  const actionColors = NODE_TYPE_COLORS.action;

  // Current position styling - purple theme (same as navigation node)
  const currentPositionStyle = {
    border: '3px solid #9c27b0',
    boxShadow: 'none', // Remove shadow
    animation: 'currentPositionPulse 2s ease-in-out infinite',
  };

  const handleScreenshotDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent node double-click from triggering
    e.preventDefault(); // Prevent default double-click behavior
    e.nativeEvent.stopImmediatePropagation(); // Stop all event propagation immediately

    console.log('[@component:UIActionNode] Screenshot double-clicked, preventing node focus');

    if (screenshotUrl) {
      setIsScreenshotModalOpen(true);
    }
  };

  const closeModal = () => {
    setIsScreenshotModalOpen(false);
  };

  // Verification indicators (same as navigation node)
  const showVerificationBadge = data.verifications && data.verifications.length > 0;
  const verificationCount = data.verifications?.length || 0;

  // Sub-tree indicators (same as navigation node)
  const showSubtreeBadge = data.has_subtree && data.subtree_count && data.subtree_count > 0;

  return (
    <>
      <div
        style={{
          // Circular shape - main difference from navigation node
          borderRadius: '50%',
          width: '120px',
          height: '120px',
          // Same styling as navigation node but adapted for circle
          background: actionColors.background,
          border: isCurrentPosition
            ? currentPositionStyle.border // Purple border for current position (highest priority)
            : `2px solid ${nodeColors.border}`, // Use validation colors for border
          padding: '12px',
          fontSize: '11px',
          color: actionColors.textColor,
          boxShadow: 'none !important', // Remove all shadows (same as navigation node)
          WebkitBoxShadow: 'none !important',
          MozBoxShadow: 'none !important',
          filter: 'none !important',
          WebkitFilter: 'none !important',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          cursor: 'pointer',
          opacity: 1,
          animation: isCurrentPosition ? currentPositionStyle.animation : 'none',
          textAlign: 'center',
        }}
        className={nodeColors.className || ''}
        data-node-type="action"
        data-node-id={id}
        title={`Action: ${data.label}${data.description ? `\n${data.description}` : ''}`}
      >
        {/* Current Position Indicator (same as navigation node) */}
        {isCurrentPosition && (
          <div
            style={{
              position: 'absolute',
              top: '8px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: '#9c27b0',
              color: 'white',
              fontSize: '10px',
              fontWeight: 'bold',
              padding: '2px 6px',
              borderRadius: '4px',
              zIndex: 15, // Same as navigation node
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: '24px',
              height: '20px',
            }}
          >
            ↓
          </div>
        )}

        {/* Verification badge - top left (same as navigation node) */}
        {showVerificationBadge && (
          <div
            style={{
              position: 'absolute',
              top: '-6px',
              left: '-6px',
              minWidth: '18px',
              height: '18px',
              borderRadius: '50%',
              backgroundColor: UI_BADGE_COLORS.verification,
              color: 'white',
              fontSize: '10px',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '2px solid white',
              zIndex: 10, // Same as navigation node badges
            }}
            title={`${verificationCount} verification${verificationCount !== 1 ? 's' : ''}`}
          >
            {verificationCount}
          </div>
        )}

        {/* Subtree badge - bottom left (same as navigation node) */}
        {showSubtreeBadge && (
          <div
            style={{
              position: 'absolute',
              bottom: '-6px',
              left: '-6px',
              minWidth: '18px',
              height: '18px',
              borderRadius: '50%',
              backgroundColor: UI_BADGE_COLORS.subtree,
              color: 'white',
              fontSize: '10px',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '2px solid white',
              zIndex: 10, // Same as navigation node badges
            }}
            title={`${data.subtree_count} subtree${data.subtree_count !== 1 ? 's' : ''}`}
          >
            {data.subtree_count}
          </div>
        )}

        {/* Action icon - center of circle */}
        <div style={{ fontSize: '32px', marginBottom: '4px' }}>⚡</div>
        
        {/* Node label - adapted for circular space */}
        <div
          style={{
            fontSize: '10px',
            fontWeight: 'bold',
            lineHeight: '1.1',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '90px',
            wordWrap: 'break-word',
            textAlign: 'center',
          }}
        >
          {data.label}
        </div>

        {/* Screenshot section (same concept as navigation node but adapted for circle) */}
        {data.screenshot && (
          <div
            style={{
              position: 'absolute',
              bottom: '8px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              overflow: 'hidden',
              border: '1px solid #ddd',
              cursor: 'pointer',
            }}
            onClick={handleScreenshotDoubleClick}
            title="Double-click to view full screenshot"
          >
            <img
              src={screenshotUrl || data.screenshot}
              alt={`Screenshot for ${data.label}`}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </div>
        )}

        {/* Node handles - EXACT same IDs as navigation node for compatibility */}
        {/* Left Handles - Overlapping for Bidirectional Effect */}
        {/* Left: TARGET for receiving connections */}
        <Handle
          type="target"
          position={Position.Left}
          id="left-target"
          isConnectable={true}
          isConnectableStart={false}
          isConnectableEnd={true}
          style={{
            background: '#1976d2',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: -7,
            top: '50%',
            transform: 'translateY(-50%)',
            cursor: 'crosshair',
            zIndex: 11,
          }}
        />

        {/* Left: SOURCE for sending connections - same position, lower z-index */}
        <Handle
          type="source"
          position={Position.Left}
          id="left-source"
          isConnectable={true}
          isConnectableStart={true}
          isConnectableEnd={false}
          style={{
            background: '#ff5722',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: -7,
            top: '50%',
            transform: 'translateY(-50%)',
            cursor: 'crosshair',
            zIndex: 10,
            opacity: 0,
          }}
        />

        {/* Right Handles - Overlapping for Bidirectional Effect */}
        {/* Right: SOURCE for sending connections */}
        <Handle
          type="source"
          position={Position.Right}
          id="right-source"
          isConnectable={true}
          isConnectableStart={true}
          isConnectableEnd={false}
          style={{
            background: '#ff5722',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            right: -7,
            top: '50%',
            transform: 'translateY(-50%)',
            cursor: 'crosshair',
            zIndex: 11,
          }}
        />

        {/* Right: TARGET for receiving connections - same position, lower z-index */}
        <Handle
          type="target"
          position={Position.Right}
          id="right-target"
          isConnectable={true}
          isConnectableStart={false}
          isConnectableEnd={true}
          style={{
            background: '#1976d2',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            right: -7,
            top: '50%',
            transform: 'translateY(-50%)',
            cursor: 'crosshair',
            zIndex: 10,
            opacity: 0,
          }}
        />

        {/* Top Handles - Overlapping */}
        {/* Top: SOURCE for menu connections */}
        <Handle
          type="source"
          position={Position.Top}
          id="top-left-menu-source"
          isConnectable={true}
          isConnectableStart={true}
          isConnectableEnd={false}
          style={{
            background: '#ff5722',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: '50%',
            transform: 'translateX(-50%)',
            top: -7,
            cursor: 'crosshair',
            zIndex: 11,
          }}
        />

        {/* Top: TARGET for menu connections - same position, lower z-index */}
        <Handle
          type="target"
          position={Position.Top}
          id="top-right-menu-target"
          isConnectable={true}
          isConnectableStart={false}
          isConnectableEnd={true}
          style={{
            background: '#4caf50',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: '50%',
            transform: 'translateX(-50%)',
            top: -7,
            cursor: 'crosshair',
            zIndex: 10,
            opacity: 0,
          }}
        />

        {/* Bottom Handles - Overlapping */}
        {/* Bottom: TARGET for menu connections */}
        <Handle
          type="target"
          position={Position.Bottom}
          id="bottom-left-menu-target"
          isConnectable={true}
          isConnectableStart={false}
          isConnectableEnd={true}
          style={{
            background: '#9c27b0',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: '50%',
            transform: 'translateX(-50%)',
            bottom: -7,
            cursor: 'crosshair',
            zIndex: 11,
          }}
        />

        {/* Bottom: SOURCE for menu connections - same position, lower z-index */}
        <Handle
          type="source"
          position={Position.Bottom}
          id="bottom-right-menu-source"
          isConnectable={true}
          isConnectableStart={true}
          isConnectableEnd={false}
          style={{
            background: '#ff5722',
            border: '2px solid #fff',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            left: '50%',
            transform: 'translateX(-50%)',
            bottom: -7,
            cursor: 'crosshair',
            zIndex: 10,
            opacity: 0,
          }}
        />
      </div>

      {/* Screenshot Modal - same as navigation node */}
      {isScreenshotModalOpen && screenshotUrl && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000, // High z-index for modal
          }}
          onClick={closeModal}
        >
          <img
            src={screenshotUrl}
            alt={`Screenshot for ${data.label}`}
            style={{
              maxWidth: '90%',
              maxHeight: '90%',
              objectFit: 'contain',
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
};