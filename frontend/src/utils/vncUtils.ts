export const calculateVncScaling = (targetSize: { width: number; height: number }) => {
  const vncResolution = { width: 1440, height: 847 };
  const scaleX = targetSize.width / vncResolution.width;
  const scaleY = targetSize.height / vncResolution.height;
  
  // Calculate positioning to center the scaled content
  const scaledWidth = vncResolution.width * scaleX;
  const scaledHeight = vncResolution.height * scaleY;
  const offsetX = (targetSize.width - scaledWidth) / 2;
  const offsetY = (targetSize.height - scaledHeight) / 2;
  
  const result = {
    transform: `translate(${offsetX}px, ${offsetY}px) scale(${scaleX}, ${scaleY})`, // Center and scale
    transformOrigin: 'top left',
    width: `${vncResolution.width}px`, // iframe needs to be VNC resolution size
    height: `${vncResolution.height}px` // iframe needs to be VNC resolution size
  };
  
  console.log(`[@utils:vncUtils] VNC scaling calculation:`, {
    targetSize,
    vncResolution,
    scales: { scaleX: scaleX.toFixed(3), scaleY: scaleY.toFixed(3) },
    scaledDimensions: `${scaledWidth.toFixed(0)}x${scaledHeight.toFixed(0)}`,
    offset: { x: offsetX.toFixed(1), y: offsetY.toFixed(1) },
    targetDimensions: `${targetSize.width}x${targetSize.height}`,
    iframeDimensions: `${result.width} x ${result.height}`,
    transform: result.transform
  });
  
  return result;
};
