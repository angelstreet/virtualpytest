// Cloudflare R2 utility functions for URL handling
// Supports both public URLs and private bucket access via pre-signed URLs
//
// MODE DETECTION (automatic based on env var):
// - If VITE_CLOUDFLARE_R2_PUBLIC_URL is set → PUBLIC mode (direct URLs, no auth needed)
// - If VITE_CLOUDFLARE_R2_PUBLIC_URL is NOT set → PRIVATE mode (signed URLs via backend)

import { api } from '../apiClient';
import { buildServerUrl } from '../buildUrlUtils';

/**
 * Get the public URL base from environment variable
 * Returns empty string if not configured (triggers private/signed URL mode)
 */
const getPublicUrlBase = (): string => {
  const envUrl = (import.meta as any).env?.VITE_CLOUDFLARE_R2_PUBLIC_URL;
  return envUrl && envUrl.trim() !== '' ? envUrl.trim().replace(/\/$/, '') : '';
};

/**
 * Check if public mode is enabled (env var is set)
 */
const isPublicModeEnabled = (): boolean => {
  return getPublicUrlBase() !== '';
};

/**
 * Configuration for signed URL behavior
 * Mode is auto-detected from VITE_CLOUDFLARE_R2_PUBLIC_URL env var
 */
const SIGNED_URL_CONFIG = {
  defaultExpiry: 3600, // 1 hour default
  cacheEnabled: true, // Cache signed URLs in memory
  cacheExpiryBuffer: 300, // Refresh 5 minutes before expiry
};

// Log mode on load
const publicUrlBase = getPublicUrlBase();
if (publicUrlBase) {
  console.log(`[@utils:cloudflareUtils] 🔓 PUBLIC mode - Using direct URLs from: ${publicUrlBase}`);
} else {
  console.log('[@utils:cloudflareUtils] 🔐 PRIVATE mode - Using signed URLs (VITE_CLOUDFLARE_R2_PUBLIC_URL not set)');
}

/**
 * In-memory cache for signed URLs
 * Structure: { path: { url, expiresAt } }
 */
const signedUrlCache: Record<string, { url: string; expiresAt: Date }> = {};

/**
 * SessionStorage key for persisting signed URL cache
 */
const CACHE_STORAGE_KEY = 'vpt_signed_url_cache';

/**
 * Load signed URL cache from sessionStorage
 */
const loadCacheFromStorage = (): void => {
  try {
    const stored = sessionStorage.getItem(CACHE_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      const now = new Date();
      
      let loadedCount = 0;
      Object.entries(parsed).forEach(([path, entry]: [string, any]) => {
        const expiresAt = new Date(entry.expiresAt);
        
        // Only load if not expired
        if (expiresAt > now) {
          signedUrlCache[path] = {
            url: entry.url,
            expiresAt: expiresAt,
          };
          loadedCount++;
        }
      });
      
      if (loadedCount > 0) {
        console.log(`[@utils:cloudflareUtils] Loaded ${loadedCount} cached signed URLs from sessionStorage`);
      }
    }
  } catch (error) {
    console.warn('[@utils:cloudflareUtils] Failed to load cache from sessionStorage:', error);
  }
};

/**
 * Save signed URL cache to sessionStorage
 */
const saveCacheToStorage = (): void => {
  try {
    // Convert Date objects to ISO strings for JSON serialization
    const serializable: Record<string, { url: string; expiresAt: string }> = {};
    
    Object.entries(signedUrlCache).forEach(([path, entry]) => {
      serializable[path] = {
        url: entry.url,
        expiresAt: entry.expiresAt.toISOString(),
      };
    });
    
    sessionStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(serializable));
  } catch (error) {
    console.warn('[@utils:cloudflareUtils] Failed to save cache to sessionStorage:', error);
  }
};

/**
 * Debounced cache save (prevents excessive writes)
 */
let saveCacheTimeout: NodeJS.Timeout | null = null;
const scheduleCacheSave = (): void => {
  if (saveCacheTimeout) {
    clearTimeout(saveCacheTimeout);
  }
  saveCacheTimeout = setTimeout(saveCacheToStorage, 500); // Save 500ms after last update
};

// Load cache from sessionStorage on initialization
loadCacheFromStorage();

/**
 * Checks if a URL is a Cloudflare R2 URL
 * @param url - The URL to check
 * @returns True if the URL is a Cloudflare R2 URL
 */
export const isCloudflareR2Url = (url: string | undefined): boolean => {
  if (!url) return false;
  return url.includes('.r2.cloudflarestorage.com') || url.includes('r2.dev');
};

/**
 * Checks if a URL is a pre-signed URL (contains AWS signature parameters)
 * @param url - The URL to check
 * @returns True if the URL contains AWS signature parameters
 */
export const isPresignedUrl = (url: string | undefined): boolean => {
  if (!url) return false;
  return url.includes('X-Amz-Signature') && url.includes('X-Amz-Expires');
};

/**
 * Extracts the relative path from a Cloudflare R2 URL
 * @param cloudflareUrl - The full Cloudflare R2 URL
 * @returns The relative path within the R2 bucket
 */
export const extractR2Path = (cloudflareUrl: string): string | null => {
  if (!isCloudflareR2Url(cloudflareUrl)) return null;

  try {
    const url = new URL(cloudflareUrl);
    // Remove leading slash from pathname
    let path = url.pathname.substring(1);
    
    // If bucket name is in path (e.g., /virtualpytest/file.jpg), remove it
    if (path.startsWith('virtualpytest/')) {
      path = path.substring('virtualpytest/'.length);
    }
    
    return path;
  } catch {
    console.error('[@utils:cloudflareUtils:extractR2Path] Invalid URL:', cloudflareUrl);
    return null;
  }
};

/**
 * Check if private/signed URL mode is active
 * Returns true if VITE_CLOUDFLARE_R2_PUBLIC_URL is NOT set
 */
export const isPrivateMode = (): boolean => !isPublicModeEnabled();

/**
 * Check if public mode is active
 * Returns true if VITE_CLOUDFLARE_R2_PUBLIC_URL IS set
 */
export const isPublicMode = (): boolean => isPublicModeEnabled();

/**
 * Get the current R2 URL mode
 */
export const getR2Mode = (): 'public' | 'private' => isPublicModeEnabled() ? 'public' : 'private';

/**
 * Check if signed URL caching is enabled
 */
export const isSignedUrlCacheEnabled = (): boolean => SIGNED_URL_CONFIG.cacheEnabled;

/**
 * Get a URL for an R2 path
 * 
 * Mode is AUTO-DETECTED based on VITE_CLOUDFLARE_R2_PUBLIC_URL env var:
 * - If env var is SET → returns public URL directly (fast, no API call)
 * - If env var is NOT SET → fetches signed URL from backend (secure, requires auth)
 * 
 * @param path - R2 path (e.g., 'captures/device1/capture_123.jpg')
 * @param expiresIn - Seconds until expiration for signed URLs (default: 3600 = 1 hour)
 * @returns Promise resolving to the URL (public or signed based on env config)
 * 
 * @example
 * const url = await getR2Url('verification/test.jpg');
 * // Returns public URL if VITE_CLOUDFLARE_R2_PUBLIC_URL is set
 * // Returns signed URL if VITE_CLOUDFLARE_R2_PUBLIC_URL is NOT set
 */
export const getR2Url = async (
  path: string,
  expiresIn: number = SIGNED_URL_CONFIG.defaultExpiry
): Promise<string> => {
  // Check if public mode is enabled (env var is set)
  const publicBase = getPublicUrlBase();
  
  if (publicBase) {
    // PUBLIC MODE: Return direct URL (no API call needed)
    return `${publicBase}/${path}`;
  }

  // PRIVATE MODE: Need to get signed URL from backend
  // Check cache first
  if (SIGNED_URL_CONFIG.cacheEnabled && signedUrlCache[path]) {
    const cached = signedUrlCache[path];
    const now = new Date();
    const timeUntilExpiry = (cached.expiresAt.getTime() - now.getTime()) / 1000;
    
    // If URL expires in more than buffer time, use cached
    if (timeUntilExpiry > SIGNED_URL_CONFIG.cacheExpiryBuffer) {
      console.log(`[@utils:cloudflareUtils] Using cached signed URL for ${path} (expires in ${Math.floor(timeUntilExpiry)}s)`);
      return cached.url;
    } else {
      // Cache expired or near expiry, remove it
      delete signedUrlCache[path];
    }
  }

  // Request new signed URL from backend
  try {
    const response = await api.post<{
      success: boolean;
      url?: string;
      expires_at?: string;
      error?: string;
    }>(buildServerUrl('/server/storage/signed-url'), {
      path,
      expires_in: expiresIn,
    });

    if (response.success && response.url && response.expires_at) {
      const { url, expires_at } = response;
      
      // Cache the result
      if (SIGNED_URL_CONFIG.cacheEnabled) {
        signedUrlCache[path] = {
          url,
          expiresAt: new Date(expires_at),
        };
        scheduleCacheSave(); // Persist to sessionStorage
      }
      
      console.log(`[@utils:cloudflareUtils] Generated signed URL for ${path} (expires: ${expires_at})`);
      return url;
    } else {
      throw new Error(response.error || 'Failed to generate signed URL');
    }
  } catch (error) {
    console.error(`[@utils:cloudflareUtils] Error generating signed URL for ${path}:`, error);
    
    // In private mode, we can't fallback to public URL - throw error
    throw new Error(`Failed to get signed URL for ${path}: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
};

/**
 * Get multiple URLs in a batch (more efficient than individual calls)
 * 
 * Mode is AUTO-DETECTED based on VITE_CLOUDFLARE_R2_PUBLIC_URL env var.
 * 
 * @param paths - Array of R2 paths
 * @param expiresIn - Seconds until expiration for signed URLs (default: 3600)
 * @returns Promise resolving to map of path -> URL
 * 
 * @example
 * const urls = await getR2UrlsBatch([
 *   'capture1.jpg',
 *   'capture2.jpg',
 *   'capture3.jpg'
 * ]);
 * console.log(urls['capture1.jpg']); // Public or signed URL based on env config
 */
export const getR2UrlsBatch = async (
  paths: string[],
  expiresIn: number = SIGNED_URL_CONFIG.defaultExpiry
): Promise<Record<string, string>> => {
  if (paths.length === 0) return {};

  // Check if public mode is enabled (env var is set)
  const publicBase = getPublicUrlBase();
  
  if (publicBase) {
    // PUBLIC MODE: Return direct URLs (no API call needed)
    return paths.reduce((acc, path) => {
      acc[path] = `${publicBase}/${path}`;
      return acc;
    }, {} as Record<string, string>);
  }

  // PRIVATE MODE: Need to get signed URLs from backend
  // Check cache for already-valid URLs
  const result: Record<string, string> = {};
  const pathsToFetch: string[] = [];
  const now = new Date();

  for (const path of paths) {
    if (SIGNED_URL_CONFIG.cacheEnabled && signedUrlCache[path]) {
      const cached = signedUrlCache[path];
      const timeUntilExpiry = (cached.expiresAt.getTime() - now.getTime()) / 1000;
      
      if (timeUntilExpiry > SIGNED_URL_CONFIG.cacheExpiryBuffer) {
        result[path] = cached.url;
      } else {
        delete signedUrlCache[path];
        pathsToFetch.push(path);
      }
    } else {
      pathsToFetch.push(path);
    }
  }

  // Fetch remaining URLs from backend (batch API)
  if (pathsToFetch.length > 0) {
    try {
      const response = await api.post<{
        success: boolean;
        urls?: Array<{ path: string; url: string; expires_at: string; expires_in: number }>;
        failed?: Array<{ path: string; error: string }>;
        generated_count?: number;
        failed_count?: number;
      }>(buildServerUrl('/server/storage/signed-urls-batch'), {
        paths: pathsToFetch,
        expires_in: expiresIn,
      });

      if (response.success && response.urls) {
        // Process successful URLs
        for (const item of response.urls) {
          result[item.path] = item.url;
          
          // Cache the result
          if (SIGNED_URL_CONFIG.cacheEnabled) {
            signedUrlCache[item.path] = {
              url: item.url,
              expiresAt: new Date(item.expires_at),
            };
          }
        }
        
        // Persist cache to sessionStorage after batch update
        if (SIGNED_URL_CONFIG.cacheEnabled && response.urls.length > 0) {
          scheduleCacheSave();
        }

        // Log failed URLs (no fallback in private mode)
        if (response.failed && response.failed.length > 0) {
          for (const failedItem of response.failed) {
            console.error(`[@utils:cloudflareUtils] Failed to get signed URL for ${failedItem.path}: ${failedItem.error}`);
            // Set to empty string to indicate failure (caller should handle)
            result[failedItem.path] = '';
          }
        }

        console.log(`[@utils:cloudflareUtils] Generated ${response.generated_count} signed URLs (batch)`);
      }
    } catch (error) {
      console.error('[@utils:cloudflareUtils] Error generating batch signed URLs:', error);
      
      // In private mode, we can't fallback - mark all as failed
      for (const path of pathsToFetch) {
        if (!result[path]) {
          result[path] = ''; // Empty string indicates failure
        }
      }
    }
  }

  return result;
};

/**
 * Clear the signed URL cache (useful when user logs out)
 */
export const clearSignedUrlCache = (): void => {
  Object.keys(signedUrlCache).forEach(key => delete signedUrlCache[key]);
  try {
    sessionStorage.removeItem(CACHE_STORAGE_KEY);
  } catch (error) {
    console.warn('[@utils:cloudflareUtils] Failed to clear sessionStorage cache:', error);
  }
  console.log('[@utils:cloudflareUtils] Signed URL cache cleared (memory + sessionStorage)');
};
