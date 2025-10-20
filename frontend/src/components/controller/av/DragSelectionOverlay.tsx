import { Box } from '@mui/material';
import React, { useState, useCallback, useRef } from 'react';

import { getZIndex } from '../../../utils/zIndexUtils';

interface DragArea {
  x: number;
  y: number;
  width: number;
  height: number;
  // Fuzzy search area (optional)
  fx?: number;
  fy?: number;
  fwidth?: number;
  fheight?: number;
}

interface DragSelectionOverlayProps {
  imageRef: React.RefObject<HTMLImageElement>;
  onAreaSelected: (area: DragArea) => void;
  selectedArea: DragArea | null;
  sx?: any;
}

export const DragSelectionOverlay: React.FC<DragSelectionOverlayProps> = ({
  imageRef,
  onAreaSelected,
  selectedArea,
  sx = {},
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDrag, setCurrentDrag] = useState<DragArea | null>(null);
  const [isHoveringImage, setIsHoveringImage] = useState(false);
  const [isFuzzyMode, setIsFuzzyMode] = useState(false); // Track if Shift key is held
  const overlayRef = useRef<HTMLDivElement>(null);

  const getImageBounds = useCallback(() => {
    if (!imageRef.current || !overlayRef.current) {
      return null;
    }

    const image = imageRef.current;
    const overlay = overlayRef.current;

    const imageRect = image.getBoundingClientRect();
    const overlayRect = overlay.getBoundingClientRect();

    // Calculate the actual displayed image dimensions (accounting for object-fit: contain)
    const imageAspectRatio = image.naturalWidth / image.naturalHeight;
    const containerAspectRatio = imageRect.width / imageRect.height;

    let displayedWidth, displayedHeight, offsetX, offsetY;

    if (imageAspectRatio > containerAspectRatio) {
      // Image is wider than container - limited by width
      displayedWidth = imageRect.width;
      displayedHeight = imageRect.width / imageAspectRatio;
      offsetX = 0;
      offsetY = (imageRect.height - displayedHeight) / 2;
    } else {
      // Image is taller than container - limited by height
      displayedWidth = imageRect.height * imageAspectRatio;
      displayedHeight = imageRect.height;
      offsetX = (imageRect.width - displayedWidth) / 2;
      offsetY = 0;
    }

    return {
      left: imageRect.left - overlayRect.left + offsetX,
      top: imageRect.top - overlayRect.top + offsetY,
      width: displayedWidth,
      height: displayedHeight,
      scaleX: image.naturalWidth / displayedWidth,
      scaleY: image.naturalHeight / displayedHeight,
    };
  }, [imageRef]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!imageRef.current) return;

      const bounds = getImageBounds();
      if (!bounds) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Detect if Shift key is pressed for fuzzy mode
      const isFuzzy = e.shiftKey;
      setIsFuzzyMode(isFuzzy);

      // Check if click is within image bounds
      if (
        x >= bounds.left &&
        x <= bounds.left + bounds.width &&
        y >= bounds.top &&
        y <= bounds.top + bounds.height
      ) {
        setIsDragging(true);
        setDragStart({ x, y });
        setCurrentDrag(null);
        e.preventDefault();
        e.stopPropagation();
      }
    },
    [imageRef, getImageBounds],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!imageRef.current) return;

      const bounds = getImageBounds();
      if (!bounds) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Check if hovering over image area
      const isOverImage =
        x >= bounds.left &&
        x <= bounds.left + bounds.width &&
        y >= bounds.top &&
        y <= bounds.top + bounds.height;
      setIsHoveringImage(isOverImage);

      // Handle dragging logic only if currently dragging
      if (!isDragging || !dragStart) return;

      // Constrain mouse to image bounds during drag
      const constrainedX = Math.max(bounds.left, Math.min(bounds.left + bounds.width, x));
      const constrainedY = Math.max(bounds.top, Math.min(bounds.top + bounds.height, y));

      const startX = Math.max(bounds.left, Math.min(bounds.left + bounds.width, dragStart.x));
      const startY = Math.max(bounds.top, Math.min(bounds.top + bounds.height, dragStart.y));

      const left = Math.min(startX, constrainedX) - bounds.left;
      const top = Math.min(startY, constrainedY) - bounds.top;
      const width = Math.abs(constrainedX - startX);
      const height = Math.abs(constrainedY - startY);

      // Minimum size constraint
      if (width >= 10 && height >= 10) {
        setCurrentDrag({ x: left, y: top, width, height });
      }
    },
    [isDragging, dragStart, imageRef, getImageBounds],
  );

  const handleMouseUp = useCallback(() => {
    if (!isDragging || !currentDrag || !imageRef.current) {
      setIsDragging(false);
      setDragStart(null);
      setCurrentDrag(null);
      setIsFuzzyMode(false);
      return;
    }

    const bounds = getImageBounds();
    if (!bounds || !onAreaSelected) {
      setIsDragging(false);
      setDragStart(null);
      setCurrentDrag(null);
      setIsFuzzyMode(false);
      return;
    }

    // Convert to original image coordinates
    const draggedArea = {
      x: currentDrag.x * bounds.scaleX,
      y: currentDrag.y * bounds.scaleY,
      width: currentDrag.width * bounds.scaleX,
      height: currentDrag.height * bounds.scaleY,
    };

    // If fuzzy mode, save to fuzzy area fields; otherwise save to exact area fields
    let updatedArea: DragArea;
    if (isFuzzyMode) {
      // Save as fuzzy area, preserve existing exact area
      updatedArea = {
        ...(selectedArea || { x: 0, y: 0, width: 0, height: 0 }),
        fx: draggedArea.x,
        fy: draggedArea.y,
        fwidth: draggedArea.width,
        fheight: draggedArea.height,
      };
      console.log('[@DragSelectionOverlay] Saved fuzzy area:', {
        fx: draggedArea.x,
        fy: draggedArea.y,
        fwidth: draggedArea.width,
        fheight: draggedArea.height,
      });
    } else {
      // Save as exact area, preserve existing fuzzy area
      updatedArea = {
        ...draggedArea,
        ...(selectedArea?.fx !== undefined && {
          fx: selectedArea.fx,
          fy: selectedArea.fy,
          fwidth: selectedArea.fwidth,
          fheight: selectedArea.fheight,
        }),
      };
      console.log('[@DragSelectionOverlay] Saved exact area:', draggedArea);
    }

    onAreaSelected(updatedArea);
    setIsDragging(false);
    setDragStart(null);
    setCurrentDrag(null);
    setIsFuzzyMode(false);
  }, [isDragging, currentDrag, imageRef, getImageBounds, onAreaSelected, isFuzzyMode, selectedArea]);

  // Display area for exact selection (white box)
  const displayExactArea =
    (!isDragging || !isFuzzyMode) && currentDrag
      ? currentDrag
      : selectedArea && getImageBounds()
      ? {
          x: selectedArea.x / getImageBounds()!.scaleX,
          y: selectedArea.y / getImageBounds()!.scaleY,
          width: selectedArea.width / getImageBounds()!.scaleX,
          height: selectedArea.height / getImageBounds()!.scaleY,
        }
      : null;

  // Display area for fuzzy selection (yellow box)
  const displayFuzzyArea =
    (isDragging && isFuzzyMode && currentDrag)
      ? currentDrag
      : selectedArea?.fx !== undefined && getImageBounds()
      ? {
          x: selectedArea.fx / getImageBounds()!.scaleX,
          y: selectedArea.fy! / getImageBounds()!.scaleY,
          width: selectedArea.fwidth! / getImageBounds()!.scaleX,
          height: selectedArea.fheight! / getImageBounds()!.scaleY,
        }
      : null;

  return (
    <Box
      ref={overlayRef}
      sx={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        cursor: isDragging ? 'crosshair' : isHoveringImage ? 'crosshair' : 'default',
        userSelect: 'none',
        pointerEvents: 'auto', // Always allow pointer events
        zIndex: getZIndex('SCREENSHOT_CAPTURE_OVERLAY'), // Above all overlays including AndroidMobileOverlay
        ...sx,
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* Fuzzy area rectangle (yellow) - render first so exact area is on top */}
      {displayFuzzyArea && getImageBounds() && (
        <Box
          sx={{
            position: 'absolute',
            left: getImageBounds()!.left + displayFuzzyArea.x,
            top: getImageBounds()!.top + displayFuzzyArea.y,
            width: displayFuzzyArea.width,
            height: displayFuzzyArea.height,
            border: '2px solid #FFD700',
            backgroundColor: 'rgba(255, 215, 0, 0.1)',
            pointerEvents: 'none',
            boxSizing: 'border-box',
            zIndex: 1,
          }}
        />
      )}

      {/* Exact area rectangle (white) */}
      {displayExactArea && getImageBounds() && (
        <Box
          sx={{
            position: 'absolute',
            left: getImageBounds()!.left + displayExactArea.x,
            top: getImageBounds()!.top + displayExactArea.y,
            width: displayExactArea.width,
            height: displayExactArea.height,
            border: '2px solid white',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            pointerEvents: 'none',
            boxSizing: 'border-box',
            zIndex: 2,
          }}
        />
      )}

      {/* Coordinates display */}
      {(displayExactArea || displayFuzzyArea) && getImageBounds() && (
        <Box
          sx={{
            position: 'absolute',
            left: getImageBounds()!.left + (displayExactArea?.x || displayFuzzyArea?.x || 0),
            top: getImageBounds()!.top + (displayExactArea?.y || displayFuzzyArea?.y || 0) - 25,
            backgroundColor: isDragging && isFuzzyMode ? 'rgba(255, 215, 0, 0.9)' : 'rgba(0, 0, 0, 0.8)',
            color: isDragging && isFuzzyMode ? 'black' : 'white',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.7rem',
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
            zIndex: 3,
            fontWeight: isDragging && isFuzzyMode ? 600 : 400,
          }}
        >
          {isDragging && isFuzzyMode
            ? '🔍 Fuzzy Search Area'
            : isDragging
            ? 'Exact Reference Area'
            : selectedArea?.fx !== undefined
            ? '⬜ Exact | 🟨 Fuzzy'
            : 'Drag to select area (hold Shift for fuzzy)'}
        </Box>
      )}
    </Box>
  );
};

export default DragSelectionOverlay;
