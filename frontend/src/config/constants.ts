/**
 * Application Constants and Configuration
 * 
 * Single source of truth for all hardcoded values, magic numbers, and configuration.
 * 
 * USAGE:
 *   import { APP_CONFIG, CACHE_CONFIG, AI_CONFIG } from '@/config/constants';
 *   const teamId = APP_CONFIG.DEFAULT_TEAM_ID;
 */

// =====================================================
// ENVIRONMENT CONFIGURATION
// =====================================================

/**
 * Get environment variable with type safety
 */
const getEnv = (key: string, defaultValue: string = ''): string => {
  try {
    return (import.meta as any).env?.[key] || defaultValue;
  } catch {
    return defaultValue;
  }
};

// =====================================================
// APPLICATION CONFIGURATION
// =====================================================

export const APP_CONFIG = {
  /**
   * Default Team ID for all API requests
   * Can be overridden via VITE_TEAM_ID environment variable
   */
  DEFAULT_TEAM_ID: getEnv('VITE_TEAM_ID', '7fdeb4bb-3639-4ec3-959f-b54769a219ce'),

  /**
   * Default User ID for session management
   * Can be overridden via VITE_USER_ID environment variable
   */
  DEFAULT_USER_ID: getEnv('VITE_USER_ID', 'eb6cfd93-44ab-4783-bd0c-129b734640f3'),

  /**
   * Default Device ID fallback
   * Used when no specific device is selected
   */
  DEFAULT_DEVICE_ID: 'device1',

  /**
   * Default user identifier for legacy APIs
   */
  DEFAULT_USER_NAME: 'default-user',

  /**
   * Default team identifier for legacy APIs
   */
  DEFAULT_TEAM_NAME: 'default-team-id',
} as const;

// =====================================================
// SERVER CONFIGURATION
// =====================================================

export const SERVER_CONFIG = {
  /**
   * Default server URL
   * Overridden by VITE_SERVER_URL environment variable or localStorage selection
   */
  DEFAULT_URL: getEnv('VITE_SERVER_URL', 'http://localhost:5109'),

  /**
   * Default server port
   */
  DEFAULT_PORT: 5109,
} as const;

// =====================================================
// CACHE CONFIGURATION (TTL in milliseconds)
// =====================================================

export const CACHE_CONFIG = {
  /**
   * Very short cache - for frequently changing data (30 seconds)
   * Used for: Host restart status, server/host data
   */
  VERY_SHORT_TTL: 30 * 1000,

  /**
   * Short cache - for dynamic data (2 minutes)
   * Used for: Currently unused (previously used for server hosts)
   */
  SHORT_TTL: 2 * 60 * 1000,

  /**
   * Medium cache - for semi-static data (5 minutes)
   * Used for: Navigation trees, navigation previews
   */
  MEDIUM_TTL: 5 * 60 * 1000,

  /**
   * Long cache - for static data (24 hours)
   * Used for: User interfaces, stream metadata
   */
  LONG_TTL: 24 * 60 * 60 * 1000,
} as const;

// =====================================================
// AI AGENT CONFIGURATION
// =====================================================

export const AI_CONFIG = {
  /**
   * Polling interval for AI execution status (2 seconds)
   */
  POLL_INTERVAL: 2000,

  /**
   * Maximum wait time for AI execution (5 minutes)
   */
  MAX_WAIT_TIME: 300000,

  /**
   * Maximum number of consecutive "not found" errors before stopping
   */
  MAX_NOT_FOUND_ATTEMPTS: 10,

  /**
   * Toast notification durations (in milliseconds)
   */
  TOAST_DURATION: {
    INFO: 3000,
    SUCCESS: 4000,
    ERROR: 5000,
    WARNING: 4000,
  },
} as const;

// =====================================================
// POLLING & RETRY CONFIGURATION
// =====================================================

export const POLLING_CONFIG = {
  /**
   * Default polling interval (2 seconds)
   */
  DEFAULT_INTERVAL: 2000,

  /**
   * Stream manifest polling interval (1 second)
   */
  STREAM_MANIFEST_INTERVAL: 1000,

  /**
   * Maximum polling attempts for stream manifest
   */
  STREAM_MANIFEST_MAX_POLLS: 15,

  /**
   * Required segments in manifest before considering stream ready
   */
  STREAM_MANIFEST_REQUIRED_SEGMENTS: 3,

  /**
   * Maximum media sequence number for "fresh" stream
   */
  STREAM_FRESH_SEQUENCE_MAX: 10,
} as const;

// =====================================================
// STREAM CONFIGURATION
// =====================================================

export const STREAM_CONFIG = {
  /**
   * Default frames per second for stream capture
   */
  DEFAULT_FPS: 5,

  /**
   * Metadata chunk duration (10 minutes in seconds)
   */
  METADATA_CHUNK_DURATION: 600,

  /**
   * Number of metadata chunks per hour
   */
  METADATA_CHUNKS_PER_HOUR: 6,

  /**
   * Maximum frames per metadata chunk (at 5fps)
   */
  METADATA_MAX_FRAMES_PER_CHUNK: 3000,
} as const;

// =====================================================
// SESSION STORAGE KEYS
// =====================================================

export const STORAGE_KEYS = {
  /**
   * Selected server URL
   */
  SELECTED_SERVER: 'selectedServer',

  /**
   * Cached user data
   */
  CACHED_USER: 'cached_user',

  /**
   * Server hosts data cache
   */
  SERVER_HOSTS_CACHE: 'serverHostsData_cache',

  /**
   * User interfaces cache
   */
  USER_INTERFACES_CACHE: 'userInterfaces_cache',

  /**
   * Stream metadata cache
   */
  STREAM_METADATA_CACHE: 'streamMetadata_cache',

  /**
   * Navigation tree cache prefix
   */
  NAVIGATION_TREE_CACHE_PREFIX: 'navTree_',

  /**
   * Navigation preview cache prefix
   */
  NAVIGATION_PREVIEW_CACHE_PREFIX: 'navPreview_',
} as const;

// =====================================================
// HTTP CONFIGURATION
// =====================================================

export const HTTP_CONFIG = {
  /**
   * Default request timeout (30 seconds)
   */
  DEFAULT_TIMEOUT: 30000,
  VERY_SHORT_TIMEOUT: 3000,
  SHORT_TIMEOUT: 10000,
  MEDIUM_TIMEOUT: 30000,
  LONG_TIMEOUT: 60000,

  /**
   * Default retry attempts for failed requests
   */
  DEFAULT_RETRY_ATTEMPTS: 3,

  /**
   * Retry delay (exponential backoff base)
   */
  RETRY_DELAY_BASE: 1000,
} as const;

// =====================================================
// TYPE EXPORTS FOR STRICT TYPE CHECKING
// =====================================================

export type AppConfig = typeof APP_CONFIG;
export type ServerConfig = typeof SERVER_CONFIG;
export type CacheConfig = typeof CACHE_CONFIG;
export type AIConfig = typeof AI_CONFIG;
export type PollingConfig = typeof POLLING_CONFIG;
export type StreamConfig = typeof STREAM_CONFIG;
export type StorageKeys = typeof STORAGE_KEYS;
export type HttpConfig = typeof HTTP_CONFIG;

