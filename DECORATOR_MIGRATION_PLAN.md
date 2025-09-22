# Decorator Migration Plan - Remove Action & Verification Services

## 🎯 **Strategy Overview**

**KEEP:** NavigationExecutor (provides real value - path finding, tree traversal)
**REMOVE:** ActionExecutor & VerificationExecutor (just expensive wrappers)
**ADD:** Decorators for logging, screenshots, and reporting

## 🏗️ **Final Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    SCRIPTS & ROUTES                         │
│  Direct controller access + NavigationExecutor              │
└─────────────────────┬───────────────────────────────────────┘
                      │ 
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              NAVIGATION SERVICE (KEEP)                      │
│  NavigationExecutor - path finding, tree traversal          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 DIRECT CONTROLLER ACCESS                    │
│  device.get_controller() with decorators                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ @action_tracking, @verification_tracking
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLLERS                              │
│  Methods decorated for automatic logging/screenshots/DB     │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 **Decorator Design**

### **1. Base Execution Decorator**
```python
# backend_host/src/lib/decorators/execution_tracking.py
import time
import functools
from typing import Any, Dict, Optional
from shared.src.lib.supabase.execution_results_db import record_action_execution, record_verification_execution

def base_execution_tracking(execution_type: str, record_func):
    """Base decorator for execution tracking"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Pre-execution
            start_time = time.time()
            method_name = func.__name__
            controller_type = self.__class__.__name__.replace('Controller', '').lower()
            
            print(f"[{controller_type.upper()}] Executing {method_name}")
            
            # Take screenshot before (if device available)
            screenshot_before = None
            if hasattr(self, 'device') and self.device:
                try:
                    av_controller = self.device.get_controller('av')
                    if av_controller:
                        screenshot_before = av_controller.take_screenshot()
                except Exception as e:
                    print(f"[{controller_type.upper()}] Screenshot before failed: {e}")
            
            # Execute original method
            try:
                result = func(self, *args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = {'success': False, 'error': str(e)}
                success = False
                error = str(e)
                print(f"[{controller_type.upper()}] {method_name} failed: {e}")
            
            # Post-execution
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Take screenshot after
            screenshot_after = None
            if hasattr(self, 'device') and self.device:
                try:
                    av_controller = self.device.get_controller('av')
                    if av_controller:
                        screenshot_after = av_controller.take_screenshot()
                except Exception as e:
                    print(f"[{controller_type.upper()}] Screenshot after failed: {e}")
            
            # Record to database
            try:
                record_func(
                    controller_type=controller_type,
                    method_name=method_name,
                    args=args,
                    kwargs=kwargs,
                    result=result,
                    success=success,
                    error=error,
                    execution_time_ms=execution_time_ms,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                    device_id=getattr(self, 'device_id', None),
                    device_model=getattr(self, 'device_model', None)
                )
            except Exception as e:
                print(f"[{controller_type.upper()}] DB recording failed: {e}")
            
            print(f"[{controller_type.upper()}] {method_name} completed in {execution_time_ms:.0f}ms")
            
            if not success:
                raise Exception(error)
                
            return result
        
        return wrapper
    return decorator
```

### **2. Specific Decorators**
```python
# Action tracking decorator
def action_tracking(func):
    """Decorator for action controller methods (remote, web, desktop, power)"""
    return base_execution_tracking('action', record_action_execution)(func)

# Verification tracking decorator  
def verification_tracking(func):
    """Decorator for verification controller methods"""
    return base_execution_tracking('verification', record_verification_execution)(func)

# AV tracking decorator (optional - for screenshots, recordings)
def av_tracking(func):
    """Decorator for AV controller methods"""
    return base_execution_tracking('av', record_action_execution)(func)
```

### **3. Usage Examples**
```python
# Remote Controller
class AndroidTVRemoteController(RemoteControllerInterface):
    
    @action_tracking
    def press_key(self, key: str) -> bool:
        return self._execute_adb_command(f"input keyevent {self._get_keycode(key)}")
    
    @action_tracking
    def input_text(self, text: str) -> bool:
        return self._execute_adb_command(f"input text '{text}'")

# Verification Controller
class VideoVerificationController(VerificationControllerInterface):
    
    @verification_tracking
    def detect_motion_from_json(self, json_count: int = 3, strict_mode: bool = False):
        # Original implementation
        return self._analyze_motion_detection(json_count, strict_mode)
    
    @verification_tracking
    def extract_subtitles(self, language: str = 'auto'):
        # Original implementation
        return self._extract_subtitle_text(language)
```

## 📁 **Files to Modify**

### **🟢 NEW FILES (3 files)**

#### **1. Decorator Implementation**
- `backend_host/src/lib/decorators/__init__.py`
- `backend_host/src/lib/decorators/execution_tracking.py`

#### **2. Database Recording Functions**
- `shared/src/lib/supabase/controller_execution_db.py` (new table for controller executions)

### **🔴 CONTROLLER FILES TO UPDATE (15+ files)**

#### **Remote Controllers:**
- `backend_host/src/controllers/remote/android_tv.py` - Add `@action_tracking`
- `backend_host/src/controllers/remote/android_mobile.py` - Add `@action_tracking`
- `backend_host/src/controllers/remote/appium_remote.py` - Add `@action_tracking`
- `backend_host/src/controllers/remote/infrared.py` - Add `@action_tracking`

#### **Web Controllers:**
- `backend_host/src/controllers/web/playwright.py` - Add `@action_tracking`

#### **Desktop Controllers:**
- `backend_host/src/controllers/desktop/bash.py` - Add `@action_tracking`
- `backend_host/src/controllers/desktop/pyautogui.py` - Add `@action_tracking`

#### **Power Controllers:**
- `backend_host/src/controllers/power/tapo_power.py` - Add `@action_tracking`

#### **Verification Controllers:**
- `backend_host/src/controllers/verification/video.py` - Add `@verification_tracking`
- `backend_host/src/controllers/verification/image.py` - Add `@verification_tracking`
- `backend_host/src/controllers/verification/text.py` - Add `@verification_tracking`
- `backend_host/src/controllers/verification/audio.py` - Add `@verification_tracking`
- `backend_host/src/controllers/verification/adb.py` - Add `@verification_tracking`
- `backend_host/src/controllers/verification/appium.py` - Add `@verification_tracking`

#### **AV Controllers (Optional):**
- `backend_host/src/controllers/audiovideo/hdmi_stream.py` - Add `@av_tracking`
- `backend_host/src/controllers/audiovideo/camera_stream.py` - Add `@av_tracking`

### **🔄 SCRIPTS & ROUTES TO UPDATE (10+ files)**

#### **Scripts - Convert to Direct Controller Access:**
- `shared/src/lib/executors/zap_executor.py` - Remove service executor usage, use direct controllers
- `test_scripts/fullzap.py` - Already uses ZapExecutor ✅
- `test_scripts/validation.py` - Check for ActionExecutor/VerificationExecutor usage

#### **Routes - Convert to Direct Controller Access:**
- `backend_host/src/routes/host_remote_routes.py` - Remove ActionExecutor, use direct controller
- `backend_host/src/routes/host_web_routes.py` - Remove ActionExecutor, use direct controller
- `backend_host/src/routes/host_desktop_routes.py` - Remove ActionExecutor, use direct controller
- `backend_host/src/routes/host_power_routes.py` - Remove ActionExecutor, use direct controller
- `backend_host/src/routes/host_verification_routes.py` - Remove VerificationExecutor, use direct controller
- `backend_host/src/routes/host_av_routes.py` - Check for service executor usage

### **🗑️ FILES TO DELETE (2 files)**
- `backend_host/src/services/actions/action_executor.py` - DELETE
- `backend_host/src/services/verifications/verification_executor.py` - DELETE

### **🔧 KEEP UNCHANGED (1 file)**
- `backend_host/src/services/navigation/navigation_executor.py` - KEEP (provides real value)

## 🚀 **Migration Phases**

### **Phase 1: Create Decorators (Day 1)**
1. Create decorator files
2. Create database recording functions
3. Test decorator on one controller

### **Phase 2: Update Controllers (Day 2-3)**
1. Add decorators to all controller methods
2. Test that decorators work correctly
3. Verify logging, screenshots, DB recording

### **Phase 3: Update Scripts & Routes (Day 4-5)**
1. Convert ZapExecutor to direct controller access
2. Convert routes to direct controller access
3. Remove ActionExecutor/VerificationExecutor imports

### **Phase 4: Cleanup (Day 6)**
1. Delete service executor files
2. Update imports and __init__.py files
3. Test full system functionality

## 📊 **Impact Analysis**

### **Lines of Code Reduction:**
- **Remove:** ~2000 lines (ActionExecutor + VerificationExecutor)
- **Add:** ~200 lines (decorators + DB functions)
- **Net Reduction:** ~1800 lines (-90%)

### **Complexity Reduction:**
- ✅ No more fake service layer
- ✅ Direct controller access
- ✅ Automatic execution tracking
- ✅ Unified logging/screenshots/DB recording

### **Functionality Preserved:**
- ✅ All controller methods work the same
- ✅ Logging, screenshots, DB recording maintained
- ✅ NavigationExecutor kept for path finding
- ✅ All existing scripts continue to work

## 🎯 **Success Criteria**

- ✅ ActionExecutor & VerificationExecutor deleted
- ✅ All controller methods decorated appropriately
- ✅ Scripts use direct controller access
- ✅ Routes use direct controller access
- ✅ NavigationExecutor preserved
- ✅ Automatic logging/screenshots/DB recording works
- ✅ ~1800 lines of code removed
- ✅ No functionality lost

---

**This plan removes the unnecessary service layer while preserving all functionality through decorators and keeping the valuable NavigationExecutor.**
