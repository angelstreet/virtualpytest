/**
 * Shared cache for testcase list data
 * 
 * Prevents multiple components from fetching the same data simultaneously
 * Implements a simple in-memory cache with TTL
 */

export interface TestCaseListCache {
  data: any;
  timestamp: number;
  teamId: string;
}

// Cache configuration
const CACHE_TTL_MS = 30000; // 30 seconds

// Single source of truth for testcase list cache
let testcaseListCache: TestCaseListCache | null = null;

// Track in-flight requests to prevent duplicate calls
let inflightRequest: Promise<any> | null = null;

/**
 * Get cached testcase list or fetch from API
 * Multiple simultaneous calls will share the same request
 */
export async function getCachedTestCaseList(
  apiUrl: string,
  teamId?: string
): Promise<any> {
  const now = Date.now();
  
  // Check if we have valid cached data
  if (testcaseListCache && 
      testcaseListCache.teamId === (teamId || 'default') &&
      (now - testcaseListCache.timestamp) < CACHE_TTL_MS) {
    console.log(`[@testcaseCache] Cache HIT (age: ${((now - testcaseListCache.timestamp) / 1000).toFixed(1)}s)`);
    return testcaseListCache.data;
  }
  
  // If there's already a request in progress, wait for it
  if (inflightRequest) {
    console.log('[@testcaseCache] Request already in flight, waiting...');
    return inflightRequest;
  }
  
  console.log('[@testcaseCache] Cache MISS - fetching fresh data');
  
  // Start new request
  inflightRequest = fetch(apiUrl)
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      
      // Update cache
      testcaseListCache = {
        data,
        timestamp: Date.now(),
        teamId: teamId || 'default',
      };
      
      console.log('[@testcaseCache] Cache updated');
      return data;
    })
    .finally(() => {
      // Clear in-flight request
      inflightRequest = null;
    });
  
  return inflightRequest;
}

/**
 * Invalidate the cache (call after create/update/delete operations)
 */
export function invalidateTestCaseListCache(): void {
  console.log('[@testcaseCache] Cache invalidated');
  testcaseListCache = null;
  inflightRequest = null;
}

/**
 * Get cache age in seconds (for debugging)
 */
export function getCacheAge(): number | null {
  if (!testcaseListCache) return null;
  return (Date.now() - testcaseListCache.timestamp) / 1000;
}



