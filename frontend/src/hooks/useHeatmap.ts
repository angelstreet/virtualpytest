/**
 * Heatmap Timeline Hook
 * 
 * Manages 24h circular buffer timeline for heatmap display.
 * Uses predictable HHMM file naming to generate timeline without API calls.
 */

import { useState, useEffect } from 'react';
import { useHostManager } from './useHostManager';

export interface TimelineItem {
  timeKey: string;        // "1425" (2:25 PM)
  displayTime: Date;      // Full date for display
  isToday: boolean;       // Whether this time is from today
  mosaicUrl: string;      // Direct R2 URL to mosaic image
  mosaicOkUrl: string;    // Direct R2 URL to OK-only mosaic
  mosaicKoUrl: string;    // Direct R2 URL to KO-only mosaic
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
  const { selectedServer } = useHostManager();
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
  
  // Get server path for R2 URLs using VITE_SERVER_URL (matches backend logic)
  const getServerPath = (): string => {
    // Use VITE_SERVER_URL directly (same source as backend)
    const viteServerUrl = (import.meta as any).env?.VITE_SERVER_URL || '';
    if (!viteServerUrl) return 'server-unknown';
    
    // Extract domain and convert to path format (same as backend)
    const match = viteServerUrl.match(/\/\/([^/?]+)/);
    if (!match) return 'server-unknown';
    
    const domain = match[1];
    const serverPath = domain.replace(/\./g, '-').replace(/:/g, '-');
    console.log(`[@useHeatmap] Using VITE_SERVER_URL: ${viteServerUrl} → ${serverPath}`);
    return serverPath;
  };
  
  
  /**
   * Generate 24-hour timeline with predictable file names
   */
  const generateTimeline = (): TimelineItem[] => {
    const now = new Date();
    const items: TimelineItem[] = [];
    const serverPath = getServerPath();
    
    // Generate 1440 minutes (24 hours)
    for (let i = 0; i < 1440; i++) {
      const time = new Date(now.getTime() - (i * 60000)); // Go back i minutes
      const timeKey = `${time.getHours().toString().padStart(2, '0')}${time.getMinutes().toString().padStart(2, '0')}`;
      
      items.push({
        timeKey,
        displayTime: time,
        isToday: time.toDateString() === now.toDateString(),
        mosaicUrl: `${R2_BASE_URL}/heatmaps/${serverPath}/${timeKey}.jpg`,
        mosaicOkUrl: `${R2_BASE_URL}/heatmaps/${serverPath}/${timeKey}_ok.jpg`,
        mosaicKoUrl: `${R2_BASE_URL}/heatmaps/${serverPath}/${timeKey}_ko.jpg`,
        analysisUrl: `${R2_BASE_URL}/heatmaps/${serverPath}/${timeKey}.json`
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
        console.log(`[useHeatmap] Successfully loaded analysis data for ${item.timeKey}:`, data);
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
   * Initialize timeline on mount and when server changes
   */
  useEffect(() => {
    const newTimeline = generateTimeline();
    setTimeline(newTimeline);
    
    // Load analysis for initial item
    if (newTimeline[currentIndex]) {
      loadAnalysisData(newTimeline[currentIndex]);
    }
  }, [selectedServer]);
  
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
  }, [currentIndex, selectedServer]);
  
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

  /**
   * Get mosaic URL based on filter
   */
  const getMosaicUrl = (item: TimelineItem | null, filter: 'ALL' | 'OK' | 'KO'): string => {
    if (!item) return '';
    
    switch (filter) {
      case 'OK': return item.mosaicOkUrl;
      case 'KO': return item.mosaicKoUrl;
      default: return item.mosaicUrl;
    }
  };

  /**
   * Filter devices based on filter type
   */
  const getFilteredDevices = (devices: any[], filter: 'ALL' | 'OK' | 'KO') => {
    if (filter === 'ALL') return devices;
    
    return devices.filter(device => {
      const analysis = device.analysis_json || {};
      const hasIncident = analysis.blackscreen || analysis.freeze || !analysis.audio;
      return filter === 'OK' ? !hasIncident : hasIncident;
    });
  };

  /**
   * Generate HTML report for current frame
   */
  const generateReport = async (): Promise<void> => {
    if (!timeline[currentIndex] || !analysisData) return;
    
    const currentItem = timeline[currentIndex];
    
    try {
      // Call backend to generate HTML report
      const response = await fetch('/server/heatmap/generateReport', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          time_key: currentItem.timeKey,
          mosaic_url: currentItem.mosaicUrl, // Always use ALL mosaic for reports
          analysis_data: analysisData,
          analysis_url: currentItem.analysisUrl,
          include_timeline: true  // Generate timeline report with 10 previous mosaics
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success && result.html_url) {
        // Open HTML report in new tab
        window.open(result.html_url, '_blank');
        console.log(`Generated HTML report for ${currentItem.timeKey}: ${result.html_url}`);
      } else {
        throw new Error(result.error || 'Failed to generate report');
      }
    } catch (error) {
      console.error('Error generating HTML report:', error);
      throw error;
    }
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
    generateReport,
    getMosaicUrl,
    getFilteredDevices,
    
    // Timeline info
    totalMinutes: timeline.length,
    isAtLatest: currentIndex === 1438,
    
    // Recovery status
    canRecover: lastSuccessfulIndex !== null && corsBlocked
  };
};
