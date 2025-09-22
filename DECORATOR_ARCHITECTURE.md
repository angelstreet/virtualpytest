# Decorator Architecture - Simplest Approach

## 🎯 **The Problem with Current Service Layer**

Current service executors are just expensive wrappers:
```python
# ActionExecutor does this:
controller = device.get_controller('remote')
result = controller.press_key('OK')
# + logging + screenshots + DB recording

# Why not just:
controller = device.get_controller('remote')
result = controller.press_key('OK')  # With decorator handling the rest
```

## 💡 **Decorator Solution - Zero Service Layer**

### **1. Execution Decorator**
```python
def with_execution_tracking(func):
    """Decorator that adds logging, screenshots, and DB recording to any controller method"""
    def wrapper(self, *args, **kwargs):
        # Pre-execution
        start_time = time.time()
        method_name = func.__name__
        print(f"[{self.__class__.__name__}] Executing {method_name}({args}, {kwargs})")
        
        # Take screenshot before (if AV controller available)
        screenshot_before = None
        if hasattr(self, 'device') and self.device:
            av_controller = self.device.get_controller('av')
            if av_controller:
                screenshot_before = av_controller.take_screenshot()
        
        # Execute original method
        result = func(self, *args, **kwargs)
        
        # Post-execution
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000
        
        # Take screenshot after
        screenshot_after = None
        if hasattr(self, 'device') and self.device:
            av_controller = self.device.get_controller('av')
            if av_controller:
                screenshot_after = av_controller.take_screenshot()
        
        # Record to database
        record_execution_to_db(
            method_name=method_name,
            args=args,
            kwargs=kwargs,
            result=result,
            execution_time_ms=execution_time,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after
        )
        
        print(f"[{self.__class__.__name__}] {method_name} completed in {execution_time:.0f}ms")
        return result
    
    return wrapper
```

### **2. Apply Decorator to Controller Methods**
```python
class AndroidTVRemoteController(RemoteControllerInterface):
    
    @with_execution_tracking
    def press_key(self, key: str) -> bool:
        """Press a key on the Android TV remote"""
        # Original implementation - no changes needed
        return self._execute_adb_command(f"input keyevent {self._get_keycode(key)}")
    
    @with_execution_tracking  
    def input_text(self, text: str) -> bool:
        """Input text on the Android TV"""
        # Original implementation - no changes needed
        return self._execute_adb_command(f"input text '{text}'")
    
    @with_execution_tracking
    def launch_app(self, package_name: str) -> bool:
        """Launch an app on the Android TV"""
        # Original implementation - no changes needed
        return self._execute_adb_command(f"monkey -p {package_name} 1")
```

### **3. Usage - Direct Controller Access**
```python
# Scripts use controllers directly - no service layer needed!
def execute_zap_iterations(context):
    device = context.selected_device
    
    # Direct controller access - decorator handles logging/screenshots/DB
    remote_controller = device.get_controller('remote')
    remote_controller.press_key('OK')  # Automatically logged, screenshotted, recorded
    
    video_controller = device.get_controller('verification_video')  
    motion_result = video_controller.detect_motion_from_json(3, False)  # Automatically tracked
    
    return motion_result
```

## 🚀 **Benefits of Decorator Approach**

### **✅ Advantages:**
1. **Zero Service Layer** - No ActionExecutor, VerificationExecutor needed
2. **No Code Duplication** - Decorator applied once per method
3. **Transparent** - Controllers work exactly the same, just with automatic tracking
4. **Simple** - One decorator handles all cross-cutting concerns
5. **Flexible** - Can be applied selectively to methods that need tracking
6. **Direct Access** - Scripts use `device.get_controller()` directly

### **🔧 Implementation Strategy:**

#### **Phase 1: Create Decorator**
- Create `@with_execution_tracking` decorator
- Add database recording function
- Test with one controller

#### **Phase 2: Apply to Controllers**  
- Add decorator to all controller methods that need tracking
- Remove service executors (ActionExecutor, VerificationExecutor)
- Update scripts to use direct controller access

#### **Phase 3: Cleanup**
- Remove service executor files
- Update routes to use direct controller access
- Update documentation

## 📁 **Files to Change**

### **🟢 NEW FILES:**
- `backend_host/src/lib/decorators/execution_tracking.py` - The decorator

### **🔴 MODIFY:**
- All controller files - Add `@with_execution_tracking` to methods
- `test_scripts/fullzap.py` - Use direct controller access
- `shared/src/lib/executors/zap_executor.py` - Use direct controller access
- All route files - Use direct controller access

### **🗑️ DELETE:**
- `backend_host/src/services/actions/action_executor.py`
- `backend_host/src/services/verifications/verification_executor.py`
- Service executor imports and usage

## 🎯 **Comparison**

| **Approach** | **Lines of Code** | **Complexity** | **Abstraction** |
|--------------|-------------------|----------------|-----------------|
| **Current Service Layer** | ~2000 lines | High | Fake (still uses get_controller) |
| **Decorator Approach** | ~100 lines | Low | None needed |
| **Direct Controller** | ~50 lines | Minimal | None |

## 💭 **The Question**

**Should we:**
1. **Decorator Approach** - Add execution tracking via decorators, remove service layer
2. **Direct Controller** - Just use `device.get_controller()` with manual logging when needed
3. **Keep Current** - Maintain the service layer despite its limitations

**The decorator approach gives us all the benefits (logging, screenshots, DB recording) without the fake service layer complexity.**

---

**This is the simplest way to get execution tracking without architectural complexity.**
