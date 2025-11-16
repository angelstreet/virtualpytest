export const calculateVncScaling = (targetSize: { width: number; height: number }) => {
  const vncResolution = { width: 1440, height: 847 };
  const scaleX = targetSize.width / vncResolution.width;
  const scaleY = targetSize.height / vncResolution.height;
  
  // Use minimum scale to maintain aspect ratio and fit within container
  const scale = Math.min(scaleX, scaleY);
  
  const result = {
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    width: `${vncResolution.width}px`,
    height: `${vncResolution.height}px`
  };
  
  console.log(`[@utils:vncUtils] VNC scaling calculation:`, {
    targetSize,
    vncResolution,
    scaleX: scaleX.toFixed(3),
    scaleY: scaleY.toFixed(3),
    selectedScale: scale.toFixed(3),
    scaledDimensions: `${Math.round(vncResolution.width * scale)}x${Math.round(vncResolution.height * scale)}`,
    targetDimensions: `${targetSize.width}x${targetSize.height}`,
    transform: result.transform
  });
  
  return result;
};
