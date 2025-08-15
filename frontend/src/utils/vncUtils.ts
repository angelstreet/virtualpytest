export const calculateVncScaling = (targetSize: { width: number; height: number }) => {
  const vncResolution = { width: 1440, height: 847 };
  const scaleX = targetSize.width / vncResolution.width;
  const scaleY = targetSize.height / vncResolution.height;
  
  // Calculate scaled dimensions
  const scaledWidth = vncResolution.width * scaleX;
  const scaledHeight = vncResolution.height * scaleY;
  
  return {
    transform: `scale(${scaleX}, ${scaleY})`, // Use both scaleX and scaleY to fill container
    transformOrigin: 'top left',
    width: `${(scaledWidth / scaleX)}px`, // Container needs to be larger to accommodate scaled content
    height: `${(scaledHeight / scaleY)}px`
  };
};
