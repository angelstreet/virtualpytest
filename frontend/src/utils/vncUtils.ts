export const calculateVncScaling = (targetSize: { width: number; height: number }) => {
  const vncResolution = { width: 1440, height: 847 };
  const scaleX = targetSize.width / vncResolution.width;
  const scaleY = targetSize.height / vncResolution.height;
  const scale = Math.min(scaleX, scaleY);
  return {
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    width: `${vncResolution.width}px`,
    height: `${vncResolution.height}px`
  };
};
