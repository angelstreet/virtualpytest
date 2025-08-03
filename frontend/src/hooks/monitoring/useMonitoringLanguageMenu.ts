import { useState, useCallback, useMemo } from 'react';

import {
  LanguageMenuAnalysis,
} from '../../types/pages/Monitoring_Types';

interface FrameRef {
  timestamp: string;
  imageUrl: string;
  jsonUrl: string;
  analysis?: any;
  languageMenuAnalysis?: LanguageMenuAnalysis | null; // Separate language menu analysis
  languageMenuDetectionPerformed?: boolean;
}

interface UseMonitoringLanguageMenuReturn {
  // Language menu detection
  analyzeLanguageMenu: () => Promise<void>;
  isAnalyzingLanguageMenu: boolean;
  hasLanguageMenuResults: boolean;
  // Current language menu analysis (from backend)
  currentLanguageMenuAnalysis: LanguageMenuAnalysis | null;
}

interface UseMonitoringLanguageMenuProps {
  frames: FrameRef[];
  currentIndex: number;
  setFrames: React.Dispatch<React.SetStateAction<FrameRef[]>>;
  setIsPlaying: (playing: boolean) => void;
  setUserSelectedFrame: (selected: boolean) => void;
  host: any;
  device: any;
}

export const useMonitoringLanguageMenu = ({
  frames,
  currentIndex,
  setFrames,
  setIsPlaying,
  setUserSelectedFrame,
  host,
  device,
}: UseMonitoringLanguageMenuProps): UseMonitoringLanguageMenuReturn => {
  const [isAnalyzingLanguageMenu, setIsAnalyzingLanguageMenu] = useState(false);

  // Check if current frame has language menu detection results
  const hasLanguageMenuResults =
    frames.length > 0 &&
    currentIndex < frames.length &&
    frames[currentIndex]?.languageMenuDetectionPerformed === true;

  // Get current language menu data
  const currentLanguageMenuAnalysis = useMemo(() => {
    if (frames.length === 0 || currentIndex >= frames.length) return null;
    const currentFrame = frames[currentIndex];
    return currentFrame?.languageMenuAnalysis || null;
  }, [frames, currentIndex]);

  // Language menu analysis function
  const analyzeLanguageMenu = useCallback(async () => {
    if (frames.length === 0 || currentIndex >= frames.length || isAnalyzingLanguageMenu) {
      return;
    }

    const currentFrame = frames[currentIndex];
    if (!currentFrame) {
      return;
    }

    // Pause the player when analyzing language menu
    setIsPlaying(false);
    setUserSelectedFrame(true);

    setIsAnalyzingLanguageMenu(true);

    try {
      console.log('[useMonitoringLanguageMenu] Analyzing language menu for frame:', currentFrame.imageUrl);

      const response = await fetch('/server/verification/video/analyzeLanguageMenu', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
          image_source_url: currentFrame.imageUrl,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('[useMonitoringLanguageMenu] Language menu analysis result:', result);

        if (result.success) {
          // Create language menu analysis using EXACT backend field names
          const newLanguageMenuData: LanguageMenuAnalysis = {
            menu_detected: result.menu_detected || false,
            audio_languages: result.audio_languages || [],
            subtitle_languages: result.subtitle_languages || [],
            selected_audio: result.selected_audio ?? -1,
            selected_subtitle: result.selected_subtitle ?? -1,
          };

          // Update the frame's language menu data and mark detection as performed
          setFrames((prev) =>
            prev.map((frame, index) =>
              index === currentIndex
                ? { 
                    ...frame, 
                    languageMenuAnalysis: newLanguageMenuData, 
                    languageMenuDetectionPerformed: true 
                  }
                : frame,
            ),
          );

          console.log(
            '[useMonitoringLanguageMenu] Updated frame with language menu data:',
            newLanguageMenuData,
          );
        } else {
          console.error('[useMonitoringLanguageMenu] Language menu analysis failed:', result.error);
        }
      } else {
        console.error(
          '[useMonitoringLanguageMenu] Language menu analysis request failed:',
          response.status,
        );
      }
    } catch (error) {
      console.error('[useMonitoringLanguageMenu] Language menu analysis error:', error);
    } finally {
      setIsAnalyzingLanguageMenu(false);
    }
  }, [
    frames,
    currentIndex,
    isAnalyzingLanguageMenu,
    host,
    device?.device_id,
    setFrames,
    setIsPlaying,
    setUserSelectedFrame,
  ]);

  return {
    analyzeLanguageMenu,
    isAnalyzingLanguageMenu,
    hasLanguageMenuResults,
    currentLanguageMenuAnalysis,
  };
};