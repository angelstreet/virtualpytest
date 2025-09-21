# Host Object Migration Plan

## COMPLETE MIGRATION PLAN: host object → host_name

### SCOPE ANALYSIS
- **Backend Routes**: 11 files with host object extraction
- **Frontend Hooks**: 18 files sending host objects  
- **Proxy Functions**: 21 files using buildHostUrl/proxy_to_host

### MIGRATION STRATEGY

#### Phase 1: Update route_utils.py
- Modify `get_host_from_request()` to expect `host_name` only
- Update `proxy_to_host()` to use host lookup by name
- Remove host object parameter passing

#### Phase 2: Backend Server Routes (11 files)
```
server_ai_routes.py - 2 endpoints
server_navigation_execution_routes.py - 2 endpoints  
server_actions_routes.py - 1 endpoint
server_control_routes.py - 4 endpoints
server_av_routes.py - 8 endpoints
server_restart_routes.py - 12 endpoints
server_monitoring_routes.py - 2 endpoints
server_remote_routes.py - 1 endpoint
server_stream_proxy_routes.py - 3 endpoints
server_translation_routes.py - 1 endpoint
server_system_routes.py - 1 endpoint
```

**Changes per file**:
- Replace `host = data.get('host')` with `host_name = data.get('host_name')`
- Remove host object validation
- Update payload forwarding to use host_name

#### Phase 3: Frontend Hooks (18 files)
```
useAI.ts - 2 API calls
useRestart.ts - 15+ API calls
useMonitoring.ts - 4 API calls
useStream.ts - 2 API calls
useHdmiStream.ts - 1 API call
usePowerControl.ts - 2 API calls
useRec.ts - 1 API call
useCampaign.ts - 1 API call
useVncStream.ts - 1 API call
useRemoteConfigs.ts - 2 API calls
usePyAutoGUI.ts - 1 API call
usePlaywrightWeb.ts - 3 API calls
useInfraredRemote.ts - 1 API call
useBashDesktop.ts - 1 API call
useAppiumRemote.ts - 4 API calls
useAndroidTv.ts - 2 API calls
useDeviceControl.ts - 2 API calls
useValidation.ts - 1 reference
```

**Changes per file**:
- Replace `host` with `host_name: host.host_name` in JSON.stringify
- Update function parameters if needed

#### Phase 4: Proxy Function Updates (21 files)
- All files using `buildHostUrl()` need host lookup
- Update `proxy_to_host()` calls to use host_name

### EXECUTION ORDER
1. **route_utils.py** - Core infrastructure
2. **Backend routes** - Server-side changes
3. **Frontend hooks** - Client-side changes  
4. **Test critical paths** - AI, navigation, actions

### MINIMAL CODE CHANGES
- **Backend**: Change `data.get('host')` → `data.get('host_name')`
- **Frontend**: Change `host` → `host_name: host.host_name`
- **No comments, no legacy code, clean implementation**

### RISK MITIGATION
- Start with AI routes (already partially done)
- Test each phase before proceeding
- Complete migration in single session

