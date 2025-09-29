# Server Manager Refactoring

## Overview
Refactored server management logic from `useDashboard` hook into a centralized `ServerManager` system following the single responsibility principle.

## Problem
- Server data fetching logic was embedded in `useDashboard.ts` (page-specific hook)
- `ServerHostData` interface was not centralized
- Server selection state was split between `HostManagerProvider` and `useDashboard`
- Difficult to reuse server management logic across different pages
- Violated separation of concerns (Dashboard managing infrastructure-level data)

## Solution
Created a dedicated `ServerManager` system with clear separation of concerns:

### Architecture

```
ServerManager (Backend Servers)     HostManager (Physical Infrastructure)
├── Server selection                ├── Host management
├── Server data fetching            ├── Device management  
├── Multi-server support            ├── Device locking
└── Server info aggregation         └── Device control
```

### New Files Created

1. **`frontend/src/types/common/Server_Types.ts`**
   - Centralized type definitions for server data
   - `ServerInfo` interface
   - `ServerHostData` interface
   - `ServerManagerState` interface

2. **`frontend/src/contexts/ServerManagerContext.ts`**
   - Context definition for server management
   - `ServerManagerContextType` interface

3. **`frontend/src/contexts/ServerManagerProvider.tsx`**
   - Server selection with localStorage persistence
   - Fetches data from all configured backend servers
   - Provides server state to the application
   - Auto-refreshes on server selection change

4. **`frontend/src/hooks/useServerManager.ts`**
   - Hook to access `ServerManager` context
   - Must be used within `ServerManagerProvider`

### Files Modified

1. **`frontend/src/App.tsx`**
   - Added `ServerManagerProvider` wrapper (outer context)
   - Provider hierarchy: `ServerManagerProvider` → `HostManagerProvider`

2. **`frontend/src/contexts/HostManagerProvider.tsx`**
   - Removed server selection state (now uses `useServerManager`)
   - Removed `getAllServerUrls` import
   - Gets `selectedServer` from `ServerManager`

3. **`frontend/src/hooks/pages/useDashboard.ts`**
   - Removed `ServerHostData` interface (moved to `Server_Types.ts`)
   - Removed server fetching logic (now in `ServerManager`)
   - Now only fetches dashboard-specific stats (campaigns, testcases, trees)
   - Uses `useServerManager` to access server data

4. **`frontend/src/pages/Dashboard.tsx`**
   - Now uses both `useServerManager` and `useDashboard`
   - Gets `serverHostsData` from `useServerManager`
   - Gets dashboard stats from `useDashboard`

## Benefits

### 1. Separation of Concerns ✅
- `ServerManager`: Backend server management
- `HostManager`: Physical infrastructure (hosts & devices)
- `useDashboard`: Dashboard-specific data (stats, recent activity)

### 2. Code Reusability ✅
- Any page can now use `useServerManager()` to access server data
- Server selection is consistent across the application
- No duplication of server fetching logic

### 3. Maintainability ✅
- Each file has a single, clear responsibility
- Server-related changes only affect `ServerManager` files
- Easier to test and debug

### 4. Smaller Files ✅
- `useDashboard.ts`: 153 lines → focused on dashboard stats
- `HostManagerProvider.tsx`: Removed 25+ lines of server logic
- Server logic centralized in `ServerManagerProvider.tsx`: ~180 lines

### 5. Independent Loading ✅
- Server data can load independently from host data
- Dashboard stats load independently from server/host data
- Better performance through parallel loading

## Usage Examples

### Accessing Server Data
```typescript
const MyComponent = () => {
  const { selectedServer, serverHostsData, isLoading } = useServerManager();
  
  // Use server data
  return <div>{/* ... */}</div>;
};
```

### Accessing Host Data
```typescript
const MyComponent = () => {
  const { getAllHosts, getDevicesByCapability } = useHostManager();
  
  // Use host data
  return <div>{/* ... */}</div>;
};
```

### Dashboard Example
```typescript
const Dashboard = () => {
  // Server management
  const { selectedServer, setSelectedServer, serverHostsData } = useServerManager();
  
  // Host management  
  const { getAllHosts } = useHostManager();
  
  // Dashboard-specific stats
  const { stats } = useDashboard();
  
  return <div>{/* ... */}</div>;
};
```

## Testing Checklist

- ✅ Dashboard displays server selector correctly
- ✅ Server selection persists to localStorage
- ✅ Server data loads from all configured servers
- ✅ Host data displays correctly per server
- ✅ Dashboard stats load correctly
- ✅ Rec page works (uses HostManager, not affected)
- ✅ Stream URLs work (regression fix maintained)
- ✅ No linter errors

## Migration Notes

### For Future Development

1. **To add server-related features**: Add to `ServerManager` files
2. **To add host-related features**: Add to `HostManager` files  
3. **To add dashboard features**: Add to `useDashboard` hook

### Breaking Changes
None - this is an internal refactoring with no API changes.

## Related Issues Fixed

1. **Regression Fix**: Maintained the fix for stream URL display issue
   - `server_url`: Full URL for API calls (functionality)
   - `server_url_display`: Clean URL for UI (display)

2. **Display Format**: Server names now show as:
   - `RPI1-server - dev.virtualpytest.com`
   - `RPI4-server - dev.virtualpytest.com/pi4-server`

## Technical Decisions

### Why ServerManager is Outside HostManager?
- **Different concerns**: Servers (API endpoints) vs Hosts (physical devices)
- **Different lifecycles**: Servers are configured, hosts register dynamically
- **Independent usage**: Some pages need only servers OR only hosts
- **Smaller files**: Each provider stays focused and manageable

### Why ServerManager Wraps HostManager?
- **Dependency**: HostManager needs `selectedServer` to fetch hosts
- **Provider hierarchy**: Child context can access parent context
- **Initialization order**: Server selection must be available before host loading

### Why Keep Server Selection in ServerManager?
- **Consistent with responsibility**: Server selection is part of server management
- **Single source of truth**: One place manages all server state
- **Better encapsulation**: Server logic is self-contained

## Date
Implemented: September 29, 2025
