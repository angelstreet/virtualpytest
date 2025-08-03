import React, { useState, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';

import { NODE_TYPE_COLORS, UI_BADGE_COLORS } from '../../config/validationColors';
import { useNavigation } from '../../contexts/navigation/NavigationContext';

import { useValidationColors } from '../../hooks/validation/useValidationColors';
import type { UINavigationNode as UINavigationNodeType, UINavigationEdge } from '../../types/pages/Navigation_Types';
import { getZIndex } from '../../utils/zIndexUtils';

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

  // Dynamic colors based on current position and validation state
  const nodeColors = React.useMemo(() => {
    return getNodeColors(id);
  }, [getNodeColors, id]);

  // Check if this is the current node
  const isCurrentNode = currentNodeId === id;

  // Dynamic styling for action nodes (circular)
  const nodeStyle: React.CSSProperties = {
    borderRadius: '50%', // Make it circular
    width: '80px',
    height: '80px',
    padding: '8px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    textAlign: 'center',
    color: '#333',
    position: 'relative',
    cursor: 'pointer',
    border: `3px solid ${nodeColors.borderColor}`,
    backgroundColor: nodeColors.backgroundColor,
    transition: 'all 0.2s ease',
    zIndex: isCurrentNode ? getZIndex('currentNode') : getZIndex('node'),
  };

  // Verification indicators
  const showVerificationBadge = data.verifications && data.verifications.length > 0;
  const verificationCount = data.verifications?.length || 0;

  // Sub-tree indicators for actions (actions shouldn't have subtrees, but keeping consistent interface)
  const showSubtreeBadge = data.has_subtree && data.subtree_count && data.subtree_count > 0;

  // Current node indicator (different styling for circular node)
  const showCurrentIndicator = isCurrentNode;

  return (
    <>
      <div
        style={nodeStyle}
        data-node-type="action"
        data-node-id={id}
        title={`Action: ${data.label}${data.description ? `\n${data.description}` : ''}`}
      >
        {/* Current node indicator - positioned for circular node */}
        {showCurrentIndicator && (
          <div
            style={{
              position: 'absolute',
              top: '-8px',
              right: '-8px',
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              backgroundColor: '#4CAF50',
              border: '2px solid white',
              zIndex: getZIndex('currentNodeIndicator'),
            }}
            title="Current Position"
          />
        )}

        {/* Verification badge - top left for circular node */}
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
              zIndex: getZIndex('verificationBadge'),
            }}
            title={`${verificationCount} verification${verificationCount !== 1 ? 's' : ''}`}
          >
            {verificationCount}
          </div>
        )}

        {/* Subtree badge - bottom left for circular node */}
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
              zIndex: getZIndex('subtreeBadge'),
            }}
            title={`${data.subtree_count} subtree${data.subtree_count !== 1 ? 's' : ''}`}
          >
            {data.subtree_count}
          </div>
        )}

        {/* Action icon - center of circle */}
        <div style={{ fontSize: '24px', marginBottom: '2px' }}>⚡</div>
        
        {/* Node label - truncated for small circular space */}
        <div
          style={{
            fontSize: '9px',
            fontWeight: 'bold',
            lineHeight: '1.1',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: '60px',
          }}
        >
          {data.label}
        </div>

        {/* Node handles - positioned for circular node */}
        <Handle
          type="target"
          position={Position.Top}
          style={{
            background: '#555',
            width: '8px',
            height: '8px',
            border: '2px solid white',
            top: '-4px',
          }}
        />
        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            background: '#555',
            width: '8px',
            height: '8px',
            border: '2px solid white',
            bottom: '-4px',
          }}
        />
      </div>

      {/* Screenshot Modal - same as other node types */}
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
            zIndex: getZIndex('screenshotModal'),
          }}
          onClick={() => setIsScreenshotModalOpen(false)}
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