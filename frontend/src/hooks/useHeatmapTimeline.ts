/**
 * Heatmap Timeline Hook
 * 
 * Manages 24h circular buffer timeline for heatmap display.
 * Uses predictable HHMM file naming to generate timeline without API calls.
 */

import { useState, useEffect } from 'react';

export interface TimelineItem {
  timeKey: string;        // "1425" (2:25 PM)
  displayTime: Date;      // Full date for display
  isToday: boolean;       // Whether this time is from today
  mosaicUrl: string;      // Direct R2 URL to mosaic image
  analysisUrl: string;    // Direct R2 URL to analysis JSON
}

export interface AnalysisData {
  time_key: string;
  timestamp: string;
  devices: Array<{
    host_name: string;
    device_id: string;
    image_url: string;
    analysis_json: {
      audio?: boolean;
      blackscreen?: boolean;
      freeze?: boolean;
      volume_percentage?: number;
      mean_volume_db?: number;
      freeze_diffs?: number[];
      last_3_filenames?: string[];
    };
  }>;
  incidents_count: number;
  hosts_count: number;
}

export const useHeatmap = () => {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(1439); // Start at latest (11:59 PM)
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  
  // Get R2 base URL from environment
  const R2_BASE_URL = import.meta.env.VITE_CLOUDFLARE_R2_PUBLIC_URL || '';
  
  /**
   * Generate 24-hour timeline with predictable file names
   */
  const generateTimeline = (): TimelineItem[] => {
    const now = new Date();
    const items: TimelineItem[] = [];
    
    // Generate 1440 minutes (24 hours)
    for (let i = 0; i < 1440; i++) {
      const time = new Date(now.getTime() - (i * 60000)); // Go back i minutes
      const timeKey = `${time.getHours().toString().padStart(2, '0')}${time.getMinutes().toString().padStart(2, '0')}`;
      
      items.push({
        timeKey,
        displayTime: time,
        isToday: time.toDateString() === now.toDateString(),
        mosaicUrl: `${R2_BASE_URL}/heatmaps/${timeKey}.jpg`,
        analysisUrl: `${R2_BASE_URL}/heatmaps/${timeKey}.json`
      });
    }
    
    return items.reverse(); // Return oldest to newest for timeline scrubber
  };
  
  /**
   * Load analysis data for current timeline item
   */
  const loadAnalysisData = async (item: TimelineItem) => {
    if (!item) return;
    
    setAnalysisLoading(true);
    try {
      const response = await fetch(item.analysisUrl);
      if (response.ok) {
        const data = await response.json();
        setAnalysisData(data);
      } else {
        setAnalysisData(null);
      }
    } catch (error) {
      console.log(`No analysis data available for ${item.timeKey}`);
      setAnalysisData(null);
    } finally {
      setAnalysisLoading(false);
    }
  };
  
  /**
   * Initialize timeline on mount
   */
  useEffect(() => {
    const newTimeline = generateTimeline();
    setTimeline(newTimeline);
    
    // Load analysis for initial item
    if (newTimeline[currentIndex]) {
      loadAnalysisData(newTimeline[currentIndex]);
    }
  }, []);
  
  /**
   * Refresh timeline every minute to get latest data
   */
  useEffect(() => {
    const interval = setInterval(() => {
      const newTimeline = generateTimeline();
      setTimeline(newTimeline);
      
      // If we're at the latest position, stay there with new data
      if (currentIndex === 1439 && newTimeline[1439]) {
        loadAnalysisData(newTimeline[1439]);
      }
    }, 60000); // Refresh every minute
    
    return () => clearInterval(interval);
  }, [currentIndex]);
  
  /**
   * Load analysis when timeline position changes
   */
  useEffect(() => {
    if (timeline[currentIndex]) {
      loadAnalysisData(timeline[currentIndex]);
    }
  }, [currentIndex, timeline]);
  
  /**
   * Navigate to specific time
   */
  const goToTime = (hours: number, minutes: number) => {
    const targetTimeKey = `${hours.toString().padStart(2, '0')}${minutes.toString().padStart(2, '0')}`;
    const targetIndex = timeline.findIndex(item => item.timeKey === targetTimeKey);
    if (targetIndex !== -1) {
      setCurrentIndex(targetIndex);
    }
  };
  
  /**
   * Navigate to latest available data
   */
  const goToLatest = () => {
    setCurrentIndex(1439); // Go to latest minute
  };
  
  /**
   * Check if current frame has incidents
   */
  const hasIncidents = (): boolean => {
    if (!analysisData) return false;
    return analysisData.incidents_count > 0;
  };
  
  return {
    // Timeline data
    timeline,
    currentIndex,
    setCurrentIndex,
    currentItem: timeline[currentIndex] || null,
    
    // Analysis data
    analysisData,
    analysisLoading,
    
    // Navigation helpers
    goToTime,
    goToLatest,
    hasIncidents,
    
    // Timeline info
    totalMinutes: timeline.length,
    isAtLatest: currentIndex === 1439
  };
};
