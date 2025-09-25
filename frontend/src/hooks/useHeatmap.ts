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
  const [currentIndex, setCurrentIndex] = useState(1438); // Start at current-1 minute
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [hasDataError, setHasDataError] = useState(false);
  const [corsBlocked, setCorsBlocked] = useState(false);
  const [retryAttempts, setRetryAttempts] = useState(0);
  const [lastSuccessfulIndex, setLastSuccessfulIndex] = useState<number | null>(null);
  
  // Get R2 base URL from environment
  const R2_BASE_URL = (import.meta as any).env?.VITE_CLOUDFLARE_R2_PUBLIC_URL || '';
  
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
   * Load analysis data with retry logic (max 10 attempts)
   * Includes CORS error detection to prevent cascade failures
   */
  const loadAnalysisData = async (item: TimelineItem, retryCount: number = 0) => {
    if (!item) return;
    
    setAnalysisLoading(true);
    try {
      const response = await fetch(item.analysisUrl, {
        mode: 'cors',
        credentials: 'omit', // Don't send credentials to prevent CORS issues
        cache: 'no-cache' // Prevent caching of failed requests
      });
      
      if (response.ok) {
        const data = await response.json();
        setAnalysisData(data);
        // Success - reset error flags and track success
        setHasDataError(false);
        setCorsBlocked(false);
        setRetryAttempts(0);
        setLastSuccessfulIndex(timeline.findIndex(t => t.timeKey === item.timeKey));
      } else if (response.status === 404 && retryCount < 10) {
        // File not generated yet, try previous minute
        const itemIndex = timeline.findIndex(t => t.timeKey === item.timeKey);
        const prevIndex = itemIndex - 1;
        if (prevIndex >= 0 && timeline[prevIndex]) {
          console.log(`File ${item.timeKey} not found, trying previous minute (attempt ${retryCount + 1})`);
          await loadAnalysisData(timeline[prevIndex], retryCount + 1);
          return;
        }
      }
      if (response.status === 404) {
        setAnalysisData(null); // Stop retrying after 10 attempts
        setHasDataError(true); // Mark as having data error
      }
    } catch (error: any) {
      // Detect CORS errors specifically
      const isCorsError = error.message?.includes('CORS') || 
                         error.message?.includes('Access-Control-Allow-Origin') ||
                         error.name === 'TypeError' && error.message?.includes('fetch');
      
      if (isCorsError) {
        console.warn(`CORS error detected for ${item.timeKey}. This may affect subsequent requests.`);
        setCorsBlocked(true);
        setRetryAttempts(prev => prev + 1);
        
        // Auto-fallback to last successful timeframe if available
        if (lastSuccessfulIndex !== null && retryAttempts < 3) {
          console.log(`Attempting fallback to last successful timeframe (index ${lastSuccessfulIndex})`);
          setTimeout(() => {
            if (timeline[lastSuccessfulIndex]) {
              loadAnalysisData(timeline[lastSuccessfulIndex], 0);
            }
          }, 1000 * Math.pow(2, retryAttempts)); // Exponential backoff
        } else {
          setAnalysisData(null);
          setHasDataError(true);
        }
      } else {
        console.log(`No analysis data available for ${item.timeKey}:`, error.message);
        setAnalysisData(null);
        setHasDataError(true);
      }
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
      if (currentIndex === 1438 && newTimeline[1438]) {
        loadAnalysisData(newTimeline[1438]);
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
   * Force refresh analysis data
   */
  const refreshCurrentData = () => {
    if (timeline[currentIndex]) {
      setAnalysisData(null); // Clear current data first
      setHasDataError(false); // Reset error flag
      setCorsBlocked(false); // Reset CORS blocked flag
      loadAnalysisData(timeline[currentIndex]);
    }
  };

  /**
   * Recovery method for CORS cascade issues
   * Call this when CORS errors block subsequent requests
   */
  const recoverFromCorsBlock = () => {
    setCorsBlocked(false);
    setHasDataError(false);
    setAnalysisData(null);
    setRetryAttempts(0);
    
    // Try to find a working timeframe by going back in time
    const findWorkingTimeframe = async () => {
      for (let i = currentIndex - 1; i >= Math.max(0, currentIndex - 60); i--) {
        if (timeline[i]) {
          try {
            const response = await fetch(timeline[i].analysisUrl, {
              mode: 'cors',
              credentials: 'omit',
              cache: 'no-cache'
            });
            if (response.ok) {
              console.log(`Found working timeframe at index ${i} (${timeline[i].timeKey})`);
              setLastSuccessfulIndex(i);
              loadAnalysisData(timeline[i], 0);
              return;
            }
          } catch (error) {
            // Continue searching
            continue;
          }
        }
      }
      console.warn('No working timeframes found. Consider refreshing the page.');
    };
    
    if (corsBlocked) {
      console.warn('CORS cascade detected. Searching for working timeframes...');
      findWorkingTimeframe();
    }
  };
  
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
   * Navigate to latest available data (current-1 minute)
   */
  const goToLatest = () => {
    setCurrentIndex(1438); // Go to current-1 minute
    setRetryAttempts(0); // Reset retry count when manually navigating
  };

  /**
   * Smart navigation that avoids problematic timeframes
   */
  const navigateToIndex = (index: number) => {
    // If CORS is blocked and we have a last successful index, suggest alternative
    if (corsBlocked && lastSuccessfulIndex !== null && Math.abs(index - lastSuccessfulIndex) > 10) {
      console.warn(`CORS issues detected. Consider using timeframe near ${timeline[lastSuccessfulIndex]?.timeKey} instead.`);
    }
    
    setCurrentIndex(index);
    setRetryAttempts(0); // Reset retry count when manually navigating
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
    setCurrentIndex: navigateToIndex, // Use smart navigation
    currentItem: timeline[currentIndex] || null,
    
    // Analysis data
    analysisData,
    analysisLoading,
    hasDataError,
    corsBlocked,
    retryAttempts,
    lastSuccessfulIndex,
    
    // Navigation helpers
    goToTime,
    goToLatest,
    hasIncidents,
    refreshCurrentData,
    recoverFromCorsBlock,
    navigateToIndex,
    
    // Timeline info
    totalMinutes: timeline.length,
    isAtLatest: currentIndex === 1438,
    
    // Recovery status
    canRecover: lastSuccessfulIndex !== null && corsBlocked
  };
};
