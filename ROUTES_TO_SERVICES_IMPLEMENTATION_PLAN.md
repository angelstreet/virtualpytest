# Routes to Services Implementation Plan

## 🎯 **Goal**
Migrate business logic from routes to services without breaking any functionality.

## 📊 **Implementation Phases**

### **Phase 1: High Priority Database Routes** (Start Here)
1. **`server_navigation_trees_routes.py`** → `navigation_service.py`
   - **Routes**: 27 routes with complex Supabase operations
   - **Logic**: Tree/node/edge CRUD operations
   - **Priority**: HIGHEST (most complex database operations)

2. **`server_device_routes.py`** → `device_service.py`
   - **Routes**: 5 routes with device CRUD
   - **Logic**: Device management operations
   - **Priority**: HIGH (core functionality)

### **Phase 2: Business Logic Routes**
3. **`server_campaign_routes.py`** → `campaign_service.py`
   - **Routes**: 5 routes with campaign management
   - **Logic**: Campaign CRUD operations

4. **`server_script_routes.py`** → `script_service.py`
   - **Routes**: 5 routes with script management
   - **Logic**: File operations, script execution

### **Phase 3: Complex Processing Routes**
5. **`server_heatmap_routes.py`** → `heatmap_service.py`
   - **Routes**: 5 routes with async processing
   - **Logic**: Complex data aggregation, async operations

6. **`server_validation_routes.py`** → `validation_service.py`
   - **Routes**: 1 route with complex cache logic
   - **Logic**: Cache management, validation processing

## 🔧 **Implementation Steps for Each Route File**

### **Step 1: Analyze Route File**
- Identify functions with business logic
- Identify database operations
- Identify complex processing

### **Step 2: Create Service File**
```python
# services/[name]_service.py
class [Name]Service:
    def method_name(self, params):
        # Move exact logic from route here
        # No changes to logic, just move it
        
# Singleton instance
[name]_service = [Name]Service()
```

### **Step 3: Update Route File**
```python
# routes/server_[name]_routes.py
@bp.route('/endpoint', methods=['POST'])
def route_function():
    try:
        # Extract request data (HTTP concern)
        data = request.get_json()
        
        # Delegate to service (business logic)
        from services.[name]_service import [name]_service
        result = [name]_service.method_name(data)
        
        # Return HTTP response (HTTP concern)
        if result['success']:
            return jsonify(result['data']), 200
        else:
            return jsonify({'error': result['error']}), result.get('status_code', 500)
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
```

### **Step 4: Test Each Migration**
- Import test: `from services.[name]_service import [name]_service`
- Route test: Verify route imports successfully
- API test: Same endpoints work identically

### **Step 5: Clean Up Legacy Code**
- Remove unused imports from routes
- Remove commented out code
- Verify no duplicate logic

## 📂 **Directory Structure After Migration**

```
backend_server/src/
├── routes/
│   ├── auto_proxy.py                    # Pure HTTP handling
│   ├── server_core_routes.py           # Minimal logic (keep)
│   ├── server_navigation_trees_routes.py # Thin routes (HTTP only)
│   ├── server_device_routes.py         # Thin routes (HTTP only)
│   └── ... (all routes become thin)
├── services/
│   ├── __init__.py
│   ├── navigation_service.py           # Complex tree operations
│   ├── device_service.py               # Device management logic
│   ├── campaign_service.py             # Campaign business logic
│   ├── script_service.py               # Script file operations
│   ├── heatmap_service.py              # Data processing logic
│   └── validation_service.py           # Validation logic
```

## ✅ **Success Criteria**

### **For Each Route File:**
- [ ] Service created with all business logic
- [ ] Route updated to use service
- [ ] Same API endpoints work identically
- [ ] No business logic remains in route
- [ ] All imports work correctly

### **Overall:**
- [ ] All routes are thin (HTTP handling only)
- [ ] All business logic is in services
- [ ] No duplicate code
- [ ] No broken functionality
- [ ] Clean import structure

## 🧪 **Testing Strategy**

### **Unit Tests**
```python
# Test service directly
def test_navigation_service():
    result = navigation_service.get_all_trees('test_team')
    assert result['success'] == True

# Test route uses service
def test_navigation_route():
    response = client.get('/server/trees?team_id=test')
    assert response.status_code == 200
```

### **Integration Tests**
- Same API responses before/after migration
- Same error handling
- Same logging behavior

## 🚨 **Risk Mitigation**

### **Low Risk Approach**
1. **One file at a time** - migrate incrementally
2. **Test after each migration** - catch issues early
3. **Keep backups** - easy rollback if needed
4. **No logic changes** - just move functions

### **Rollback Plan**
If any migration breaks:
1. Restore original route file from backup
2. Remove service file
3. Update imports back to original

## 📊 **Expected Results**

### **Before Migration**
- Business logic scattered across route files
- Hard to test business logic (mixed with HTTP)
- Difficult to reuse logic
- Routes are fat (100+ lines each)

### **After Migration**
- Clean separation of concerns
- Easy to test business logic
- Reusable service methods
- Routes are thin (20-30 lines each)

**Ready to start Phase 1 implementation!**
