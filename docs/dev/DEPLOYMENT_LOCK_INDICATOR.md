# Deployment Lock Indicator Feature

## Overview
Shows a lock icon 🔒 on devices when a deployment script is currently running on them.

## How It Works

### Backend Flow

1. **Deployment Tracking** (`deployment_scheduler.py`)
   - When a deployment executes, it creates a record in `deployment_executions` table with `status: 'running'`
   - The record links to a `deployment_id`, which contains `host_name` and `device_id`
   - When complete, status changes to `'completed'` or `'failed'`

2. **Status Check** (`backend_host/src/lib/utils/host_utils.py`)
   - New function `get_devices_with_running_deployments()`:
     ```python
     # Queries Supabase for running executions
     # Returns a set of device_ids that have active deployments
     ```

3. **Ping Data Update** (`backend_host/src/lib/utils/host_utils.py`)
   - During heartbeat ping (every ~10 seconds):
     - Checks which devices have running deployments
     - Adds `has_running_deployment: boolean` to each device in ping data
     - Sends to server

4. **Server Processing** (`backend_server/src/lib/utils/server_utils.py`)
   - Server's `update_host_ping()` method updates device status
   - Stores `has_running_deployment` flag in the host registry
   - Flag is included when frontend fetches host data via `/server/system/getAllHosts`

### Frontend Flow

1. **Type Definition** (`frontend/src/types/common/Host_Types.ts`)
   ```typescript
   export interface Device {
     // ... existing fields
     has_running_deployment?: boolean; // New field
   }
   ```

2. **UI Components**

   **RecHostPreview** - Shows lock icon in device card header:
   ```tsx
   {device?.has_running_deployment && (
     <LockIcon 
       sx={{ fontSize: '0.9rem', color: 'warning.main' }} 
       titleAccess="Script running"
     />
   )}
   ```
   
   **RecHostStreamModal** - Shows lock icon in modal header:
   ```tsx
   {device?.has_running_deployment && (
     <LockIcon 
       sx={{ fontSize: '1.1rem', color: 'warning.main' }} 
       titleAccess="Script running"
     />
   )}
   ```

## Visual Appearance

### Device Preview Card
```
┌─────────────────────────────────────┐
│ Device Name - Host  [flags] 🔒 ✓   │ ← Lock icon here
│                                     │
│        [Video Stream Preview]       │
│                                     │
└─────────────────────────────────────┘
```

### Stream Modal
```
┌────────────────────────────────────────┐
│ Device Name - 🔒 Live   [controls] ×  │ ← Lock icon here
├────────────────────────────────────────┤
│                                        │
│         [Full Screen Stream]           │
│                                        │
└────────────────────────────────────────┘
```

## Icon Details
- **Color**: Orange (warning.main)
- **Size**: 0.9rem (preview), 1.1rem (modal)
- **Tooltip**: "Script running"
- **Position**: Between device name and mode indicator

## Update Frequency
- Status refreshes every ~10 seconds via host ping
- Near real-time indicator (max 10-second delay)

## Code Changes Summary

### Backend
1. `backend_host/src/lib/utils/host_utils.py`
   - Added `get_devices_with_running_deployments()` function
   - Modified `send_ping_to_server()` to include device deployment status

2. `backend_server/src/lib/utils/server_utils.py`
   - Updated `update_host_ping()` to process device deployment status

### Frontend
1. `frontend/src/types/common/Host_Types.ts`
   - Added `has_running_deployment?: boolean` to Device interface

2. `frontend/src/components/rec/RecHostPreview.tsx`
   - Added LockIcon import
   - Added lock icon display in header

3. `frontend/src/components/rec/RecStreamModalHeader.tsx`
   - Added LockIcon import
   - Added lock icon display in modal title

## Benefits
- **Minimal Code Changes**: Only ~50 lines of code across 5 files
- **Real-time Feedback**: Users can see which devices are busy
- **Visual Clarity**: Prevents confusion about device availability
- **Non-intrusive**: Small icon that doesn't clutter the UI

## Testing
1. Create a deployment on a device
2. Verify lock icon appears in preview card (within 10 seconds)
3. Open stream modal - verify lock icon appears in header
4. Wait for deployment to complete
5. Verify lock icon disappears (within 10 seconds)

