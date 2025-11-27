/**
 * API Client with Automatic JWT Authentication
 * 
 * Wraps fetch() to automatically include Supabase JWT token in Authorization header.
 * Use this for all API calls to backend_server that require user authentication.
 * 
 * Usage:
 *   import { apiClient } from '@/utils/apiClient';
 *   
 *   // Instead of fetch()
 *   const response = await apiClient(buildServerUrl('/server/devices'), {
 *     method: 'POST',
 *     body: JSON.stringify({ ... })
 *   });
 */

import { supabase, isAuthEnabled } from '../lib/supabase';

export interface ApiClientOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
  skipAuth?: boolean; // Skip adding Authorization header
}

/**
 * Enhanced fetch with automatic JWT authentication
 */
export async function apiClient(
  url: string,
  options: ApiClientOptions = {}
): Promise<Response> {
  const { skipAuth = false, headers = {}, ...fetchOptions } = options;

  // Prepare headers
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Add Authorization header with JWT token (unless skipped or auth disabled)
  if (!skipAuth && isAuthEnabled) {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        requestHeaders['Authorization'] = `Bearer ${session.access_token}`;
        console.log('[@apiClient] Added JWT token to request');
      } else {
        console.warn('[@apiClient] No active session - request will be unauthenticated');
      }
    } catch (error) {
      console.error('[@apiClient] Error getting session:', error);
      // Continue without auth header
    }
  } else if (!isAuthEnabled) {
    // Auth disabled - no token to add
    console.log('[@apiClient] Auth disabled - no JWT token added');
  }

  // Make the request
  return fetch(url, {
    ...fetchOptions,
    headers: requestHeaders,
  });
}

/**
 * API Client with JSON parsing
 * Convenience method that parses JSON response automatically
 */
export async function apiClientJson<T = any>(
  url: string,
  options: ApiClientOptions = {}
): Promise<T> {
  const response = await apiClient(url, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Typed API Client Methods
 */
export const api = {
  /**
   * GET request with auth
   */
  get: async <T = any>(url: string, options?: ApiClientOptions): Promise<T> => {
    return apiClientJson<T>(url, { ...options, method: 'GET' });
  },

  /**
   * POST request with auth
   */
  post: async <T = any>(url: string, data?: any, options?: ApiClientOptions): Promise<T> => {
    return apiClientJson<T>(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  /**
   * PUT request with auth
   */
  put: async <T = any>(url: string, data?: any, options?: ApiClientOptions): Promise<T> => {
    return apiClientJson<T>(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  /**
   * DELETE request with auth
   */
  delete: async <T = any>(url: string, options?: ApiClientOptions): Promise<T> => {
    return apiClientJson<T>(url, { ...options, method: 'DELETE' });
  },
};

/**
 * Example Usage:
 * 
 * // Simple GET
 * const devices = await api.get(buildServerUrl('/server/devices/getAllDevices'));
 * 
 * // POST with data
 * const result = await api.post(buildServerUrl('/server/devices/control'), {
 *   device_id: 'device1',
 *   action: 'restart'
 * });
 * 
 * // Skip auth for public endpoints
 * const publicData = await api.get(buildServerUrl('/server/health'), { skipAuth: true });
 * 
 * // Custom headers
 * const data = await api.get(url, {
 *   headers: { 'X-Custom-Header': 'value' }
 * });
 */

