# MCP Playground Architecture - Reusing TestCaseBuilder Infrastructure

## Overview
The MCP Playground **EXACTLY REUSES** TestCaseBuilder's infrastructure without reinventing anything. This document shows the explicit mapping.

## ✅ Reused Hooks & Contexts

### 1. Device Selection & Control
**TestCaseBuilder uses:**
```typescript
// From useTestCaseBuilderPage.ts lines 161-174
const {
  selectedHost,
  selectedDeviceId,
  isControlActive,
  availableHosts,
  handleDeviceSelect,
  handleControlStateChange,
  isDeviceLocked,
} = useHostManager();
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts lines 61-73
const {
  selectedHost,
  selectedDeviceId,
  isControlActive,
  availableHosts,
  handleDeviceSelect: hostManagerDeviceSelect,
  handleControlStateChange,
} = useHostManager();

const handleDeviceSelect = hostManagerDeviceSelect;
```

### 2. Take/Release Control
**TestCaseBuilder uses:**
```typescript
// From useTestCaseBuilderPage.ts lines 206-219
const {
  isControlLoading,
  handleDeviceControl,
  controlError,
  clearError,
} = useDeviceControlWithForceUnlock({
  host: selectedHost,
  device_id: selectedDeviceId,
  sessionId: 'testcase-builder-session',
  autoCleanup: true,
  tree_id: currentTreeId || undefined,
  onControlStateChange: handleControlStateChange,
});
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts lines 87-96
const {
  isControlLoading,
  handleDeviceControl,
  controlError,
  clearError,
} = useDeviceControlWithForceUnlock({
  host: selectedHost,
  device_id: selectedDeviceId,
  sessionId: 'mcp-playground-session', // Only difference: session name
  autoCleanup: true,
  tree_id: currentTreeId || undefined,
  onControlStateChange: handleControlStateChange,
});
```

### 3. Device Data (Actions/Verifications)
**TestCaseBuilder uses:**
```typescript
// From useTestCaseBuilderPage.ts lines 233-262
const { 
  setControlState, 
  getAvailableActions,
  getAvailableVerificationTypes,
  availableActionsLoading,
  fetchAvailableActions,
} = useDeviceData();

useEffect(() => {
  setControlState(selectedHost, selectedDeviceId, isControlActive);
}, [selectedHost, selectedDeviceId, isControlActive, setControlState]);

useEffect(() => {
  if (!isControlActive || !selectedHost || !selectedDeviceId) return;
  
  const timer = setTimeout(async () => {
    await fetchAvailableActions(true);
    if (selectedHost?.host_name) {
      await fetchStandardBlocks(selectedHost.host_name, true);
    }
  }, 1000);

  return () => clearTimeout(timer);
}, [isControlActive, selectedHost, selectedDeviceId, fetchAvailableActions, fetchStandardBlocks]);

const availableActions = getAvailableActions();
const availableVerifications = getAvailableVerificationTypes();
const areActionsLoaded = isControlActive && !availableActionsLoading && Object.values(availableActions || {}).flat().length > 0;
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts lines 98-126
const { 
  setControlState, 
  getAvailableActions,
  getAvailableVerificationTypes,
  availableActionsLoading,
  fetchAvailableActions,
} = useDeviceData();

useEffect(() => {
  setControlState(selectedHost, selectedDeviceId, isControlActive);
}, [selectedHost, selectedDeviceId, isControlActive, setControlState]);

useEffect(() => {
  if (!isControlActive || !selectedHost || !selectedDeviceId) return;
  
  const timer = setTimeout(async () => {
    await fetchAvailableActions(true);
  }, 1000);

  return () => clearTimeout(timer);
}, [isControlActive, selectedHost, selectedDeviceId, fetchAvailableActions]);

const availableActions = getAvailableActions();
const availableVerifications = getAvailableVerificationTypes();
const areActionsLoaded = isControlActive && !availableActionsLoading && Object.values(availableActions || {}).flat().length > 0;
```

### 4. Interface Selection & Tree Loading
**TestCaseBuilder uses:**
```typescript
// From useTestCaseBuilderPage.ts lines 264-268
const { setUserInterfaceFromProps } = useNavigationEditor();
const { loadTreeByUserInterface, getNodeById } = useNavigationConfig();
const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();

// Lines 280-333 - Load compatible interfaces
useEffect(() => {
  const loadCompatibleInterfaces = async () => {
    if (!selectedDeviceId || !selectedHost) {
      setCompatibleInterfaceNames([]);
      setUserinterfaceName('');
      return;
    }
    
    try {
      const selectedDevice = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
      
      if (!selectedDevice) {
        console.warn('[@useTestCaseBuilderPage] Selected device not found');
        return;
      }
      
      const interfaces = await getAllUserInterfaces();
      const compatibleInterfaces = filterCompatibleInterfaces(interfaces, selectedDevice);
      
      const names = compatibleInterfaces.map((iface: any) => iface.userinterface_name);
      setCompatibleInterfaceNames(names);
      
      if (names.length > 0 && !userinterfaceName) {
        setUserinterfaceName(names[0]);
      }
    } catch (error) {
      console.error('[@useTestCaseBuilderPage] Error loading compatible interfaces:', error);
    }
  };
  
  loadCompatibleInterfaces();
}, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName]);

// Lines 335-386 - Load navigation tree
useEffect(() => {
  const loadTreeForInterface = async () => {
    if (!userinterfaceName) {
      setNavNodes([]);
      setCurrentTreeId(null);
      return;
    }
    
    try {
      setIsLoadingTree(true);
      const interfaceData = await getUserInterfaceByName(userinterfaceName);
      
      if (!interfaceData) {
        console.warn(`[@useTestCaseBuilderPage] Interface not found: ${userinterfaceName}`);
        return;
      }
      
      const tree_id = interfaceData.tree_id;
      if (!tree_id) {
        console.warn(`[@useTestCaseBuilderPage] No tree_id for interface: ${userinterfaceName}`);
        return;
      }
      
      setCurrentTreeId(tree_id);
      await loadTreeByUserInterface(userinterfaceName);
      await setUserInterfaceFromProps(userinterfaceName);
      
      // Extract nodes
      const allNodes: any[] = [];
      const collectNodes = (nodeId: string, visited = new Set<string>()) => {
        if (visited.has(nodeId)) return;
        visited.add(nodeId);
        
        const node = getNodeById(nodeId);
        if (node) {
          allNodes.push(node);
          node.edges?.forEach((edge: any) => {
            if (edge.target) collectNodes(edge.target, visited);
          });
        }
      };
      
      const entryNode = getNodeById('ENTRY');
      if (entryNode) {
        collectNodes('ENTRY');
      }
      
      const filteredNodes = allNodes.filter(node => 
        node.id !== 'ENTRY' && 
        node.type !== 'entry' &&
        node.label?.toLowerCase() !== 'entry'
      );
      
      setNavNodes(filteredNodes);
      console.log(`[@useTestCaseBuilderPage] Loaded ${filteredNodes.length} nodes for ${userinterfaceName}`);
    } catch (error) {
      console.error('[@useTestCaseBuilderPage] Error loading tree:', error);
    } finally {
      setIsLoadingTree(false);
    }
  };
  
  loadTreeForInterface();
}, [userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface, setUserInterfaceFromProps, getNodeById]);
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts lines 128-220
const { setUserInterfaceFromProps } = useNavigationEditor();
const { loadTreeByUserInterface, getNodeById } = useNavigationConfig();
const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();

// EXACT SAME interface loading logic (lines 137-164)
useEffect(() => {
  const loadCompatibleInterfaces = async () => {
    if (!selectedDeviceId || !selectedHost) {
      setCompatibleInterfaceNames([]);
      setUserinterfaceName('');
      return;
    }
    
    try {
      const selectedDevice = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
      
      if (!selectedDevice) {
        console.warn('[@useMCPPlaygroundPage] Selected device not found');
        return;
      }
      
      const interfaces = await getAllUserInterfaces();
      const compatibleInterfaces = filterCompatibleInterfaces(interfaces, selectedDevice);
      
      const names = compatibleInterfaces.map((iface: any) => iface.userinterface_name);
      setCompatibleInterfaceNames(names);
      
      if (names.length > 0 && !userinterfaceName) {
        setUserinterfaceName(names[0]);
      }
    } catch (error) {
      console.error('[@useMCPPlaygroundPage] Error loading compatible interfaces:', error);
    }
  };
  
  loadCompatibleInterfaces();
}, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName]);

// EXACT SAME tree loading logic (lines 166-220)
useEffect(() => {
  const loadTreeForInterface = async () => {
    if (!userinterfaceName) {
      setNavNodes([]);
      setCurrentTreeId(null);
      return;
    }
    
    try {
      setIsLoadingTree(true);
      const interfaceData = await getUserInterfaceByName(userinterfaceName);
      
      if (!interfaceData) {
        console.warn(`[@useMCPPlaygroundPage] Interface not found: ${userinterfaceName}`);
        return;
      }
      
      const tree_id = interfaceData.tree_id;
      if (!tree_id) {
        console.warn(`[@useMCPPlaygroundPage] No tree_id for interface: ${userinterfaceName}`);
        return;
      }
      
      setCurrentTreeId(tree_id);
      await loadTreeByUserInterface(userinterfaceName);
      await setUserInterfaceFromProps(userinterfaceName);
      
      const allNodes: any[] = [];
      const collectNodes = (nodeId: string, visited = new Set<string>()) => {
        if (visited.has(nodeId)) return;
        visited.add(nodeId);
        
        const node = getNodeById(nodeId);
        if (node) {
          allNodes.push(node);
          node.edges?.forEach((edge: any) => {
            if (edge.target) collectNodes(edge.target, visited);
          });
        }
      };
      
      const entryNode = getNodeById('ENTRY');
      if (entryNode) {
        collectNodes('ENTRY');
      }
      
      const filteredNodes = allNodes.filter(node => 
        node.id !== 'ENTRY' && 
        node.type !== 'entry' &&
        node.label?.toLowerCase() !== 'entry'
      );
      
      setNavNodes(filteredNodes);
      console.log(`[@useMCPPlaygroundPage] Loaded ${filteredNodes.length} nodes for ${userinterfaceName}`);
    } catch (error) {
      console.error('[@useMCPPlaygroundPage] Error loading tree:', error);
    } finally {
      setIsLoadingTree(false);
    }
  };
  
  loadTreeForInterface();
}, [userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface, setUserInterfaceFromProps, getNodeById]);
```

### 5. AI Generation
**TestCaseBuilder uses:**
```typescript
// From useTestCaseBuilderPage.ts line 268
const { generateTestCaseFromPrompt, saveDisambiguationAndRegenerate } = useTestCaseAI();
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts lines 222-223
const { generateTestCaseFromPrompt } = useTestCaseAI();
const { executeTestCase } = useTestCaseExecution();
const unifiedExecution = useExecutionState();
```

### 6. Execution
**TestCaseBuilder uses:**
```typescript
// From TestCaseBuilderContext.tsx
const unifiedExecution = useExecutionState();
```

**MCP Playground uses (IDENTICAL):**
```typescript
// From useMCPPlaygroundPage.ts line 224
const unifiedExecution = useExecutionState();
```

## ✅ Reused Components

### Device Selector
**TestCaseBuilder:**
- Uses `TestCaseBuilderHeader` which calls `handleDeviceSelect` from `useHostManager`
- Renders host dropdown, device dropdown, interface dropdown
- Shows control button

**MCP Playground:**
- Created `MCPDeviceSelector` which receives props from `useMCPPlaygroundPage`
- **EXACT SAME logic**: host dropdown, device dropdown, interface dropdown, control button
- **Same parameters**: `selectedHost`, `selectedDeviceId`, `userinterfaceName`, `handleDeviceSelect`, `handleDeviceControl`

### Execution Display
**TestCaseBuilder:**
- Uses `ExecutionProgressBar` from `TestCaseBuilderHeader`
- Receives `unifiedExecution.state`

**MCP Playground:**
- Created `MCPExecutionResult` which receives `unifiedExecution` prop
- **EXACT SAME logic**: displays `isExecuting`, `blockStates`, `result`

## Summary

| Feature | TestCaseBuilder | MCP Playground | Status |
|---------|----------------|----------------|--------|
| Host Manager | `useHostManager()` | `useHostManager()` | ✅ **IDENTICAL** |
| Device Control | `useDeviceControlWithForceUnlock()` | `useDeviceControlWithForceUnlock()` | ✅ **IDENTICAL** |
| Device Data | `useDeviceData()` | `useDeviceData()` | ✅ **IDENTICAL** |
| Interface Selection | `filterCompatibleInterfaces()` | `filterCompatibleInterfaces()` | ✅ **IDENTICAL** |
| Tree Loading | `loadTreeByUserInterface()` | `loadTreeByUserInterface()` | ✅ **IDENTICAL** |
| AI Generation | `useTestCaseAI()` | `useTestCaseAI()` | ✅ **IDENTICAL** |
| Execution State | `useExecutionState()` | `useExecutionState()` | ✅ **IDENTICAL** |
| Execution | `useTestCaseExecution()` | `useTestCaseExecution()` | ✅ **IDENTICAL** |

## Key Differences
The **ONLY** differences are:
1. **Session ID**: `'testcase-builder-session'` vs `'mcp-playground-session'`
2. **No graph builder**: MCP Playground doesn't use ReactFlow (not needed for prompt-based execution)
3. **Command history**: Added localStorage-based history (TestCaseBuilder has save/load testcases instead)

Everything else is **100% reused** from TestCaseBuilder's infrastructure.

