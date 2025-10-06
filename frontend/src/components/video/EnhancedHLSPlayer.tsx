import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';
import { MonitoringOverlay } from '../monitoring/MonitoringOverlay';
import { useStream } from '../../hooks/controller';
import { buildStreamUrl } from '../../utils/buildUrlUtils';
import { EnhancedHLSPlayerProps } from './EnhancedHLSPlayer.types';
import { useArchivePlayer } from './hooks/useArchivePlayer';
import { useTranscriptPlayer } from './hooks/useTranscriptPlayer';
import { TimelineOverlay } from './overlays/TimelineOverlay';
import { TranscriptOverlay } from './overlays/TranscriptOverlay';
import { LanguageSelector } from './overlays/LanguageSelector';

export const EnhancedHLSPlayer: React.FC<EnhancedHLSPlayerProps> = ({
  deviceId,
  hostName,
  host,
  streamUrl: providedStreamUrl,
  width = '100%',
  height = 400,
  muted = true,
  className,
  isLiveMode: externalIsLiveMode,
  quality = 'sd',
  shouldPause = false,
  onPlayerReady,
  onVideoTimeUpdate,
  onVideoPause,
  
  monitoringMode = false,
  monitoringAnalysis,
  subtitleAnalysis,
  languageMenuAnalysis,
  aiDescription,
  errorTrendData,
  analysisTimestamp,
  isAIAnalyzing = false,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [internalIsLiveMode] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const qualityTimestampRef = useRef<number>(Date.now());
  const [isAtLiveEdge, setIsAtLiveEdge] = useState(true);
  const liveEdgeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [liveBufferSeconds, setLiveBufferSeconds] = useState(0);
  const [liveSliderPosition, setLiveSliderPosition] = useState(150);
  
  const isLiveMode = externalIsLiveMode !== undefined ? externalIsLiveMode : internalIsLiveMode;
  
  const prevIsLiveMode = useRef(isLiveMode);
  const prevQuality = useRef(quality);
  
  useEffect(() => {
    if (prevQuality.current !== quality) {
      console.log(`[@EnhancedHLSPlayer] Quality changed: ${prevQuality.current} -> ${quality}`);
      qualityTimestampRef.current = Date.now();
      prevQuality.current = quality;
    }
  }, [quality]);

  const { streamUrl: hookStreamUrl } = useStream({
    host: host || {
      host_name: hostName,
      host_url: `http://${hostName}:6109`,
      host_port: 6109,
      devices: [],
      device_count: 0,
      status: 'online',
      last_seen: Date.now(),
      registered_at: new Date().toISOString(),
      system_stats: {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        platform: 'linux',
        architecture: 'x86_64',
        python_version: '3.9'
      },
      isLocked: false
    },
    device_id: deviceId,
  });

  const archive = useArchivePlayer({
    isLiveMode,
    providedStreamUrl,
    hookStreamUrl: hookStreamUrl || undefined,
    host,
    deviceId,
    isTransitioning,
    videoRef,
    onVideoTimeUpdate,
  });

  const transcript = useTranscriptPlayer({
    isLiveMode,
    archiveMetadata: archive.archiveMetadata,
    currentManifestIndex: archive.currentManifestIndex,
    globalCurrentTime: archive.globalCurrentTime,
    providedStreamUrl,
    hookStreamUrl: hookStreamUrl || undefined,
    host,
    deviceId,
    hostName,
  });

  useEffect(() => {
    if (prevIsLiveMode.current !== isLiveMode) {
      console.log(`[@EnhancedHLSPlayer] Mode change detected: ${prevIsLiveMode.current ? 'Live' : 'Archive'} -> ${isLiveMode ? 'Live' : 'Archive'}`);
      setIsTransitioning(true);
      
      if (isLiveMode) {
        archive.clearArchiveData();
        transcript.clearTranscriptData();
      }
      
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
      
      prevIsLiveMode.current = isLiveMode;
    }
  }, [isLiveMode, archive, transcript]);

  // Listen for pause event to trigger AI analysis (one call only)
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !onVideoPause) return;

    const handlePlay = () => {
      console.log('[@EnhancedHLSPlayer] Video playing');
      setIsPlaying(true);
    };

    const handlePause = () => {
      console.log('[@EnhancedHLSPlayer] Video paused - triggering AI analysis callback');
      setIsPlaying(false);
      onVideoPause(); // Single call when paused (no parameters)
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, [onVideoPause]);

  const streamUrl = useMemo(() => {
    let url: string;
    
    if (isLiveMode) {
      if (providedStreamUrl) {
        url = providedStreamUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/output.m3u8');
      } else if (hookStreamUrl) {
        url = hookStreamUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/output.m3u8');
      } else {
        url = buildStreamUrl(host, deviceId);
      }
    }
    else if (archive.archiveMetadata && archive.archiveMetadata.manifests.length > 0) {
      const currentManifest = archive.archiveMetadata.manifests[archive.currentManifestIndex];
      if (currentManifest) {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        const chunkPath = currentManifest.name;
        url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${chunkPath}`);
        console.log(`[@EnhancedHLSPlayer] Using 10-min chunk (hour ${currentManifest.window_index}, chunk ${currentManifest.chunk_index}):`, url);
      } else {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        const firstHour = archive.availableHours.length > 0 ? archive.availableHours[0] : 0;
        url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${firstHour}/chunk_10min_0.mp4`);
      }
    }
    else {
      const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
      const firstHour = archive.availableHours.length > 0 ? archive.availableHours[0] : 0;
      url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${firstHour}/chunk_10min_0.mp4`);
    }
    
    const separator = url.includes('?') ? '&' : '?';
    url = `${url}${separator}q=${quality}&t=${qualityTimestampRef.current}`;
    
    return url;
  }, [providedStreamUrl, hookStreamUrl, isLiveMode, deviceId, archive.archiveMetadata, archive.currentManifestIndex, quality, archive.availableHours, host]);

  const seekToLive = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      if (video.duration && !isNaN(video.duration) && isFinite(video.duration)) {
        video.currentTime = video.duration;
      }
    }
  };

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleLiveSliderChange = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    const value = Array.isArray(newValue) ? newValue[0] : newValue;
    const minAllowed = Math.max(0, 150 - liveBufferSeconds);
    const clampedValue = Math.max(value, minAllowed);
    setLiveSliderPosition(clampedValue);
    archive.handleSliderChange(_event, clampedValue);
    setIsAtLiveEdge(clampedValue >= 145);
  }, [archive, liveBufferSeconds]);

  const handleLiveSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current) return;
    
    const value = Array.isArray(newValue) ? newValue[0] : newValue;
    const video = videoRef.current;
    
    if (video.buffered.length > 0) {
      const buffered = video.buffered;
      const bufferEnd = buffered.end(buffered.length - 1);
      const bufferStart = buffered.start(0);
      
      const secondsBehind = 150 - value;
      const targetTime = bufferEnd - secondsBehind;
      
      console.log(`[@EnhancedHLSPlayer] Live seek to ${value}s position (${secondsBehind}s behind live)`);
      video.currentTime = Math.max(bufferStart, Math.min(targetTime, bufferEnd));
      setLiveSliderPosition(value);
      
      if (value >= 145) {
        video.currentTime = bufferEnd - 1;
        setLiveSliderPosition(150);
      }
    }
    
    archive.handleSeek(_event, newValue);
  }, [archive, videoRef]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      
      if (isLiveMode && video.buffered.length > 0) {
        const buffered = video.buffered;
        const bufferEnd = buffered.end(buffered.length - 1);
        const bufferStart = buffered.start(0);
        const totalBuffer = bufferEnd - bufferStart;
        const latency = bufferEnd - video.currentTime;
        const atLiveEdge = latency < 3;
        
        setLiveBufferSeconds(totalBuffer);
        
        if (atLiveEdge !== isAtLiveEdge) {
          setIsAtLiveEdge(atLiveEdge);
          console.log(`[@EnhancedHLSPlayer] Live edge status: ${atLiveEdge ? 'LIVE' : 'BEHIND'} (latency: ${latency.toFixed(2)}s)`);
        }
      }
      
      if (!isLiveMode) {
        archive.updateTimeTracking(video);
      }
    };
    
    const handleDurationChange = () => {
      setDuration(video.duration);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('error', archive.handleVideoError);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('error', archive.handleVideoError);
      
      if (liveEdgeTimeoutRef.current) {
        clearTimeout(liveEdgeTimeoutRef.current);
      }
    };
  }, [isLiveMode, archive, isAtLiveEdge]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLiveMode) {
        console.log('[@EnhancedHLSPlayer] Switching to live mode');
        setIsAtLiveEdge(true);
        setLiveBufferSeconds(0);
        setLiveSliderPosition(150);
        seekToLive();
      } else {
        if (videoRef.current && videoRef.current.duration) {
          console.log(`[@EnhancedHLSPlayer] Mode change to archive, seeking to beginning`);
          videoRef.current.currentTime = 0;
        }
      }
    }, 500);
    
    return () => clearTimeout(timer);
  }, [isLiveMode]);

  return (
    <Box className={className} sx={{ width, position: 'relative' }}>
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
        `}
      </style>
      
      <Box sx={{ position: 'relative', height }}>
        {!isTransitioning && (!archive.isCheckingAvailability && (isLiveMode || archive.availableHours.length > 0)) ? (
          <HLSVideoPlayer
            key={`${isLiveMode ? 'live' : 'archive'}`}
            streamUrl={streamUrl}
            isStreamActive={true}
            videoElementRef={videoRef}
            muted={muted}
            isArchiveMode={!isLiveMode}
            shouldPause={shouldPause}
            sx={{ width: '100%', height: '100%' }}
            onPlayerReady={onPlayerReady}
          />
        ) : (
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'black',
              color: 'white',
            }}
          >
            {archive.isCheckingAvailability ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <CircularProgress sx={{ color: 'white' }} />
                <Typography>Checking available archive hours...</Typography>
              </Box>
            ) : archive.availableHours.length === 0 && !isLiveMode ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <Typography>No archive hours available</Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Switch back to Live mode or check again later
                </Typography>
              </Box>
            ) : (
              <Typography>Switching mode...</Typography>
            )}
          </Box>
        )}

        <LanguageSelector
          transcriptData={transcript.transcriptData}
          selectedLanguage={transcript.selectedLanguage}
          isTranslating={transcript.isTranslating}
          onLanguageChange={transcript.handleLanguageChange}
          show={!isLiveMode}
        />

        {monitoringMode && isLiveMode && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 100,
            }}
          >
            <MonitoringOverlay
              monitoringAnalysis={monitoringAnalysis || undefined}
              subtitleAnalysis={subtitleAnalysis}
              languageMenuAnalysis={languageMenuAnalysis}
              consecutiveErrorCounts={errorTrendData || undefined}
              showSubtitles={!!subtitleAnalysis}
              showLanguageMenu={!!languageMenuAnalysis}
              analysisTimestamp={analysisTimestamp || undefined}
              isAIAnalyzing={isAIAnalyzing}
            />

            {aiDescription && (
              <Box
                sx={{
                  position: 'absolute',
                  top: 16,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  maxWidth: '60%',
                  minWidth: 300,
                  p: 1,
                  backgroundColor: 'rgba(0, 0, 0, 0.75)',
                  borderRadius: 1,
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  textAlign: 'center',
                  zIndex: 30,
                  pointerEvents: 'none',
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: '#ffffff',
                    fontSize: '0.7rem',
                    lineHeight: 1.2,
                    fontWeight: 400,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {aiDescription}
                </Typography>
              </Box>
            )}
          </Box>
        )}

        <TranscriptOverlay
          currentTranscript={transcript.currentTranscript}
          transcriptText={transcript.getCurrentTranscriptText()}
          selectedLanguage={transcript.selectedLanguage}
          show={!isLiveMode}
        />

        <TimelineOverlay
          isLiveMode={isLiveMode}
          isPlaying={isPlaying}
          currentTime={currentTime}
          duration={duration}
          isAtLiveEdge={isAtLiveEdge}
          liveBufferSeconds={liveBufferSeconds}
          liveSliderPosition={liveSliderPosition}
          globalCurrentTime={archive.globalCurrentTime}
          isDraggingSlider={archive.isDraggingSlider}
          dragSliderValue={archive.dragSliderValue}
          archiveMetadata={archive.archiveMetadata}
          availableHours={archive.availableHours}
          hourMarks={archive.hourMarks}
          videoRef={videoRef}
          onTogglePlayPause={togglePlayPause}
          onSliderChange={isLiveMode ? handleLiveSliderChange : archive.handleSliderChange}
          onSeek={isLiveMode ? handleLiveSeek : archive.handleSeek}
          show={!isTransitioning}
          currentManifestIndex={archive.currentManifestIndex}
        />
      </Box>
    </Box>
  );
};