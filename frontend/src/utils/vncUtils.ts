export const calculateVncScaling = (targetSize: { width: number; height: number }) => {
  const vncResolution = { width: 1440, height: 847 };
  const scaleX = targetSize.width / vncResolution.width;
  const scaleY = targetSize.height / vncResolution.height;
  
  const result = {
    transform: `scale(${scaleX}, ${scaleY})`, // Use both scaleX and scaleY to fill container
    transformOrigin: 'top left',
    width: `${vncResolution.width}px`, // iframe needs to be VNC resolution size
    height: `${vncResolution.height}px` // iframe needs to be VNC resolution size
  };
  
  console.log(`[@utils:vncUtils] VNC scaling calculation:`, {
    targetSize,
    vncResolution,
    scales: { scaleX: scaleX.toFixed(3), scaleY: scaleY.toFixed(3) },
    targetDimensions: `${targetSize.width}x${targetSize.height}`,
    iframeDimensions: `${result.width} x ${result.height}`,
    transform: result.transform
  });
  
  return result;
};
