import React, { createContext, useContext, useCallback, useRef } from 'react';
import { NavigationStep } from '../../types/pages/Navigation_Types';

interface NavigationPreviewCacheContextType {
  getCachedPreview: (treeId: string, currentNodeId: string | null, targetNodeId: string) => NavigationStep[] | null;
  cachePreview: (treeId: string, currentNodeId: string | null, targetNodeId: string, steps: NavigationStep[]) => void;
  invalidateTree: (treeId: string) => void;
}

const NavigationPreviewCacheContext = createContext<NavigationPreviewCacheContextType | null>(null);

export const NavigationPreviewCacheProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const cache = useRef<Map<string, NavigationStep[]>>(new Map());

  const getCachedPreview = useCallback((treeId: string, currentNodeId: string | null, targetNodeId: string) => {
    const key = `${treeId}|${currentNodeId || 'root'}|${targetNodeId}`;
    const cached = cache.current.get(key);
    if (cached) console.log(`[@PreviewCache] ✅ HIT: ${targetNodeId}`);
    return cached || null;
  }, []);

  const cachePreview = useCallback((treeId: string, currentNodeId: string | null, targetNodeId: string, steps: NavigationStep[]) => {
    const key = `${treeId}|${currentNodeId || 'root'}|${targetNodeId}`;
    cache.current.set(key, steps);
    console.log(`[@PreviewCache] Cached ${targetNodeId} (total: ${cache.current.size})`);
  }, []);

  const invalidateTree = useCallback((treeId: string) => {
    const keys = Array.from(cache.current.keys()).filter(k => k.startsWith(`${treeId}|`));
    keys.forEach(k => cache.current.delete(k));
    console.log(`[@PreviewCache] Invalidated ${keys.length} entries for tree ${treeId}`);
  }, []);

  return (
    <NavigationPreviewCacheContext.Provider value={{ getCachedPreview, cachePreview, invalidateTree }}>
      {children}
    </NavigationPreviewCacheContext.Provider>
  );
};

export const useNavigationPreviewCache = () => {
  const context = useContext(NavigationPreviewCacheContext);
  if (!context) throw new Error('useNavigationPreviewCache must be used within NavigationPreviewCacheProvider');
  return context;
};
